from fastapi import APIRouter, HTTPException
from typing import Any
from app.schemas import ComputeIn, ComputeOut
from app.deps.supabase_client import get_supabase
from app.services.gee import analyze_polygon
from app.services.carbon import compute_carbon

router = APIRouter(prefix="/compute", tags=["compute"])

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

    # Analyze metrics via GEE
    try:
        metrics = analyze_polygon(geometry)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Compute carbon figures
    fire = payload.fire_risk if payload.fire_risk is not None else 0.05
    drought = payload.drought_risk if payload.drought_risk is not None else 0.03
    trend = payload.trend_loss if payload.trend_loss is not None else 0.02

    computed, risks = compute_carbon(metrics, area_m2, fire_risk=fire, drought_risk=drought, trend_loss=trend)

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
        "carbon_biomass": computed["carbon_biomass"],
        "soc_total": computed["soc_total"],
        "annual_co2": computed["annual_co2"],
        "co2_20yr": computed["co2_20yr"],
        "risk_adjusted_co2": computed["risk_adjusted_co2"],
    }

    try:
        res = sb.table("project_results").insert(row).select("*").single().execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to store results")
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
