from fastapi import APIRouter, HTTPException
from app.schemas import ProjectCreate, ProjectOut
from app.deps.supabase_client import get_supabase

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("", response_model=ProjectOut)
def create_project(payload: ProjectCreate):
    sb = get_supabase()
    try:
        data = {
            "user_id": payload.user_id,
            "name": payload.name,
            "description": payload.description,
        }
        res = sb.table("projects").insert(data).select("id,user_id,name,description").single().execute()
        if not res.data:
            raise HTTPException(status_code=500, detail="Failed to create project")
        return res.data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ProjectOut])
def list_projects(user_id: str):
    sb = get_supabase()
    try:
        res = sb.table("projects").select("id,user_id,name,description").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
