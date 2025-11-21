from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.schemas import PolygonCreate, PolygonOut, PolygonOutWithGeometry
from app.deps.supabase_client import get_supabase
from app.utils.geo import normalize_geometry, clean_and_validate, to_geojson

router = APIRouter(prefix="/polygons", tags=["polygons"])

@router.get("/{polygon_id}", response_model=PolygonOutWithGeometry)
def get_polygon(polygon_id: str):
    sb = get_supabase()
    try:
        res = sb.table("project_polygons").select("id,project_id,area_m2,bbox,geometry").eq("id", polygon_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Polygon not found")
        return res.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[PolygonOutWithGeometry])
def list_polygons(project_id: Optional[str] = Query(None)):
    sb = get_supabase()
    try:
        query = sb.table("project_polygons").select("id,project_id,area_m2,bbox,geometry")
        if project_id:
            query = query.eq("project_id", project_id)
        # Order by created_at descending
        query = query.order("created_at", desc=True)
        res = query.execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=PolygonOut)
def create_polygon(payload: PolygonCreate):
    sb = get_supabase()
    try:
        geom_in = normalize_geometry(payload.geometry)
        geom, area_m2, bbox = clean_and_validate(geom_in)
        geom_gj = to_geojson(geom)

        record = {
            "project_id": payload.project_id,
            "geometry": geom_gj,
            "bbox": bbox,
            "area_m2": area_m2,
            "srid": 4326,
        }
        res = sb.table("project_polygons").insert(record).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to store polygon")
        # Return the inserted row
        inserted = res.data[0]
        return {
            "id": inserted["id"],
            "project_id": inserted["project_id"],
            "area_m2": inserted["area_m2"],
            "bbox": inserted["bbox"],
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
