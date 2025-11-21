from fastapi import APIRouter, HTTPException
from app.schemas import PolygonCreate, PolygonOut
from app.deps.supabase_client import get_supabase
from app.utils.geo import normalize_geometry, clean_and_validate, to_geojson

router = APIRouter(prefix="/polygons", tags=["polygons"])

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
        res = sb.table("project_polygons").insert(record).select("id,project_id,area_m2,bbox").single().execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to store polygon")
        return res.data
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
