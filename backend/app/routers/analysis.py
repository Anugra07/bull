from fastapi import APIRouter, HTTPException
from typing import Any
from app.schemas import AnalysisIn, AnalysisOut
from app.deps.supabase_client import get_supabase
from app.services.gee import analyze_polygon

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.post("", response_model=AnalysisOut)
def run_analysis(payload: AnalysisIn) -> Any:
    sb = get_supabase()

    # Resolve geometry
    geometry = payload.geometry
    if not geometry and payload.polygon_id:
        try:
            res = sb.table("project_polygons").select("geometry").eq("id", payload.polygon_id).single().execute()
            if not res.data or not res.data.get("geometry"):
                raise HTTPException(status_code=404, detail="Polygon not found")
            geometry = res.data["geometry"]
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to load polygon: {e}")

    if not geometry:
        raise HTTPException(status_code=422, detail="Provide either polygon_id or geometry")

    try:
        metrics = analyze_polygon(geometry)
        return metrics
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
