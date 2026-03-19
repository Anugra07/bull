from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional, List
from datetime import datetime, timezone
from app.schemas import ComputeIn, ComputeOut, ComputeDirectIn
from app.deps.supabase_client import get_supabase
from app.services.gee import analyze_polygon
from app.services.carbon import compute_carbon
from app.utils.geo import normalize_geometry, clean_and_validate

router = APIRouter(prefix="/compute", tags=["compute"])


def _insert_project_result_with_fallback(sb: Any, row: dict) -> Any:
    """
    Insert result row while tolerating schema-cache lag (PGRST204 unknown column).
    Retries by dropping only the missing column reported by PostgREST.
    """
    row_working = dict(row)
    max_retries = 25

    for _ in range(max_retries):
        try:
            return sb.table("project_results").insert(row_working).execute()
        except Exception as e:
            msg = str(e)
            marker = "Could not find the '"
            if "PGRST204" in msg and marker in msg and "' column" in msg:
                col = msg.split(marker, 1)[1].split("' column", 1)[0]
                if col in row_working:
                    row_working.pop(col, None)
                    continue
            raise

    raise HTTPException(status_code=500, detail="Failed to insert project_results after schema fallback retries")


def _compute_from_geometry(
    geometry: Any,
    area_m2: float,
    soil_depth: str,
    fire_risk: float | None,
    drought_risk: float | None,
    trend_loss: float | None,
) -> tuple[dict, dict, dict]:
    # Analyze metrics via GEE
    metrics = analyze_polygon(geometry, soil_depth=soil_depth)

    # Apply model inference before carbon accounting.
    from app.services.inference import get_inference_engine

    inference = get_inference_engine().predict(metrics)
    metrics = inference["metrics"]

    computed, risks = compute_carbon(
        metrics,
        area_m2,
        fire_risk=fire_risk,
        drought_risk=drought_risk,
        trend_loss=trend_loss,
        apply_ml=False,
    )
    risks["ml_models_used"] = bool(inference.get("ml_models_used"))
    return metrics, computed, inference

@router.get("", response_model=List[ComputeOut])
def get_results(project_id: Optional[str] = Query(None)) -> Any:
    sb = get_supabase()
    try:
        query = sb.table("project_results").select("*")
        if project_id:
            query = query.eq("project_id", project_id)
        # Order by created_at descending
        query = query.order("created_at", desc=True)
        res = query.execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=ComputeOut)
def compute(payload: ComputeIn) -> Any:
    sb = get_supabase()

    # Load polygon geometry and area
    try:
        poly_res = sb.table("project_polygons").select("geometry, area_m2").eq("id", payload.polygon_id).single().execute()
        if not poly_res.data:
            raise HTTPException(status_code=404, detail="Polygon not found")
        geometry = poly_res.data["geometry"]
        area_m2 = float(poly_res.data.get("area_m2") or 0.0)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to load polygon: {e}")

    try:
        metrics, computed, inference = _compute_from_geometry(
            geometry=geometry,
            area_m2=area_m2,
            soil_depth=payload.soil_depth,
            fire_risk=payload.fire_risk,
            drought_risk=payload.drought_risk,
            trend_loss=payload.trend_loss,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Build row for project_results
    row = {
        "project_id": payload.project_id,
        "ndvi": metrics.get("ndvi"),
        "evi": metrics.get("evi"),
        "biomass": metrics.get("biomass"),
        "canopy_height": metrics.get("canopy_height"),
        "soc": metrics.get("soc"),
        "bulk_density": metrics.get("bulk_density"),
        "rainfall": metrics.get("rainfall"),
        "elevation": metrics.get("elevation"),
        "slope": metrics.get("slope"),
        "land_cover": metrics.get("land_cover"),
        # Time-series trends
        "ndvi_trend": metrics.get("ndvi_trend"),
        "ndvi_trend_interpretation": metrics.get("ndvi_trend_interpretation"),
        "fire_burn_percent": metrics.get("fire_burn_percent"),
        "fire_recent_burn": metrics.get("fire_recent_burn"),
        "rainfall_anomaly_percent": metrics.get("rainfall_anomaly_percent"),
        "trend_classification": metrics.get("trend_classification"),
        # Carbon calculations
        "carbon_biomass": computed["carbon_biomass"],
        "soc_total": computed["soc_total"],
        "annual_co2": computed["annual_co2"],
        "co2_20yr": computed["co2_20yr"],
        "risk_adjusted_co2": computed["risk_adjusted_co2"],
        "ecosystem_type": computed.get("ecosystem_type"),
        "baseline_condition": computed.get("baseline_condition"),
        # Baseline Carbon Stock (MRV)
        "baseline_biomass_carbon": computed.get("baseline_biomass_carbon"),
        "baseline_soc_total": computed.get("baseline_soc_total"),
        "baseline_annual_co2": computed.get("baseline_annual_co2"),
        "baseline_co2_20yr": computed.get("baseline_co2_20yr"),
        "baseline_scenario": computed.get("baseline_scenario"),
        # Project Carbon Stock
        "project_annual_co2": computed.get("project_annual_co2"),
        "project_co2_20yr": computed.get("project_co2_20yr"),
        # Additionality (Carbon Credits)
        "additionality_annual_co2": computed.get("additionality_annual_co2"),
        "additionality_20yr": computed.get("additionality_20yr"),
        # QA/QC Metrics
        "pixel_count": metrics.get("pixel_count"),
        "ndvi_stddev": metrics.get("ndvi_stddev"),
        "soc_stddev": metrics.get("soc_stddev"),
        "rainfall_stddev": metrics.get("rainfall_stddev"),
        "cloud_coverage_percent": metrics.get("cloud_coverage_percent"),
        "gedi_shot_count": metrics.get("gedi_shot_count"),
        "data_confidence_score": metrics.get("data_confidence_score"),
        # ML inference metadata and derived fields
        "ml_models_used": bool(inference.get("ml_models_used")),
        "biomass_source": inference.get("biomass_source"),
        "soc_source": inference.get("soc_source"),
        "model_version_biomass": inference.get("model_version_biomass"),
        "model_version_soc": inference.get("model_version_soc"),
        "biomass_aboveground": metrics.get("biomass_aboveground"),
        "biomass_belowground": metrics.get("biomass_belowground"),
        "biomass_total": metrics.get("biomass_total"),
        "soil_depth_applied": metrics.get("soil_depth_applied"),
    }

    biomass_interval = inference.get("biomass_interval") or {}
    soc_interval = inference.get("soc_interval") or {}
    if biomass_interval:
        row.update({
            "prediction_interval_biomass_lower_95": biomass_interval.get("lower_95"),
            "prediction_interval_biomass_upper_95": biomass_interval.get("upper_95"),
            "prediction_interval_biomass_width": biomass_interval.get("interval_width"),
        })
    if soc_interval:
        row.update({
            "prediction_interval_soc_lower_95": soc_interval.get("lower_95"),
            "prediction_interval_soc_upper_95": soc_interval.get("upper_95"),
            "prediction_interval_soc_width": soc_interval.get("interval_width"),
        })

    try:
        res = _insert_project_result_with_fallback(sb, row)
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to store results")
        # Return the inserted row - convert to ComputeOut format
        inserted = dict(res.data[0])
        # Ensure API response still includes computed ML fields even if DB schema is behind.
        for key, value in row.items():
            inserted.setdefault(key, value)
        return inserted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/direct", response_model=ComputeOut)
def compute_direct(payload: ComputeDirectIn) -> Any:
    """
    Direct compute path that bypasses Supabase polygon lookup/storage.
    Useful for end-to-end validation in environments with restricted DB egress.
    """
    try:
        geom_in = normalize_geometry(payload.geometry)
        geom, area_m2, _ = clean_and_validate(geom_in)
        geometry = {
            "type": geom.geom_type,
            "coordinates": geom.__geo_interface__["coordinates"],
        }
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid geometry: {e}")

    try:
        metrics, computed, inference = _compute_from_geometry(
            geometry=geometry,
            area_m2=area_m2,
            soil_depth=payload.soil_depth,
            fire_risk=payload.fire_risk,
            drought_risk=payload.drought_risk,
            trend_loss=payload.trend_loss,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    response = {
        "id": f"direct-{int(datetime.now(timezone.utc).timestamp())}",
        "project_id": payload.project_id or "direct",
        "ndvi": metrics.get("ndvi"),
        "evi": metrics.get("evi"),
        "biomass": metrics.get("biomass"),
        "biomass_aboveground": metrics.get("biomass_aboveground"),
        "biomass_belowground": metrics.get("biomass_belowground"),
        "biomass_total": metrics.get("biomass_total"),
        "biomass_source": inference.get("biomass_source"),
        "soc_source": inference.get("soc_source"),
        "model_version_biomass": inference.get("model_version_biomass"),
        "model_version_soc": inference.get("model_version_soc"),
        "ml_models_used": bool(inference.get("ml_models_used")),
        "canopy_height": metrics.get("canopy_height"),
        "soc": metrics.get("soc"),
        "soc_details": metrics.get("soc_details"),
        "soil_depth_applied": metrics.get("soil_depth_applied"),
        "bulk_density": metrics.get("bulk_density"),
        "rainfall": metrics.get("rainfall"),
        "elevation": metrics.get("elevation"),
        "slope": metrics.get("slope"),
        "land_cover": metrics.get("land_cover"),
        "ecosystem_type": computed.get("ecosystem_type"),
        "carbon_biomass": computed.get("carbon_biomass"),
        "soc_total": computed.get("soc_total"),
        "annual_co2": computed.get("annual_co2"),
        "co2_20yr": computed.get("co2_20yr"),
        "risk_adjusted_co2": computed.get("risk_adjusted_co2"),
        "ndvi_trend": metrics.get("ndvi_trend"),
        "ndvi_trend_interpretation": metrics.get("ndvi_trend_interpretation"),
        "fire_burn_percent": metrics.get("fire_burn_percent"),
        "fire_recent_burn": metrics.get("fire_recent_burn"),
        "rainfall_anomaly_percent": metrics.get("rainfall_anomaly_percent"),
        "trend_classification": metrics.get("trend_classification"),
        "pixel_count": metrics.get("pixel_count"),
        "ndvi_stddev": metrics.get("ndvi_stddev"),
        "soc_stddev": metrics.get("soc_stddev"),
        "rainfall_stddev": metrics.get("rainfall_stddev"),
        "cloud_coverage_percent": metrics.get("cloud_coverage_percent"),
        "gedi_shot_count": metrics.get("gedi_shot_count"),
        "data_confidence_score": metrics.get("data_confidence_score"),
        "baseline_condition": computed.get("baseline_condition"),
        "baseline_biomass_carbon": computed.get("baseline_biomass_carbon"),
        "baseline_soc_total": computed.get("baseline_soc_total"),
        "baseline_annual_co2": computed.get("baseline_annual_co2"),
        "baseline_co2_20yr": computed.get("baseline_co2_20yr"),
        "baseline_scenario": computed.get("baseline_scenario"),
        "project_annual_co2": computed.get("project_annual_co2"),
        "project_co2_20yr": computed.get("project_co2_20yr"),
        "additionality_annual_co2": computed.get("additionality_annual_co2"),
        "additionality_20yr": computed.get("additionality_20yr"),
    }

    biomass_interval = inference.get("biomass_interval") or {}
    soc_interval = inference.get("soc_interval") or {}
    response.update({
        "prediction_interval_biomass_lower_95": biomass_interval.get("lower_95"),
        "prediction_interval_biomass_upper_95": biomass_interval.get("upper_95"),
        "prediction_interval_biomass_width": biomass_interval.get("interval_width"),
        "prediction_interval_soc_lower_95": soc_interval.get("lower_95"),
        "prediction_interval_soc_upper_95": soc_interval.get("upper_95"),
        "prediction_interval_soc_width": soc_interval.get("interval_width"),
    })
    return response
