from fastapi import APIRouter, HTTPException, Query
from typing import Any, Optional, List
from app.schemas import ComputeIn, ComputeOut
from app.deps.supabase_client import get_supabase
from app.services.gee import analyze_polygon
from app.services.carbon import compute_carbon

router = APIRouter(prefix="/compute", tags=["compute"])

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

    # Analyze metrics via GEE
    try:
        metrics = analyze_polygon(geometry, soil_depth=payload.soil_depth)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    # Compute carbon figures - ecosystem-specific defaults will be used if not provided
    computed, risks = compute_carbon(
        metrics, 
        area_m2, 
        fire_risk=payload.fire_risk,
        drought_risk=payload.drought_risk,
        trend_loss=payload.trend_loss
    )

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
        "carbon_biomass": computed["carbon_biomass"],
        "soc_total": computed["soc_total"],
        "annual_co2": computed["annual_co2"],
        "co2_20yr": computed["co2_20yr"],
        "risk_adjusted_co2": computed["risk_adjusted_co2"],
    }
    # Add ecosystem_type if available (may need database column added)
    if "ecosystem_type" in computed:
        row["ecosystem_type"] = computed["ecosystem_type"]

    try:
        res = sb.table("project_results").insert(row).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to store results")
        # Return the inserted row - convert to ComputeOut format
        inserted = res.data[0]
        return inserted
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
