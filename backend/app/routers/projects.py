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
        # Insert - Supabase returns the inserted row by default
        res = sb.table("projects").insert(data).execute()
        if not res.data or len(res.data) == 0:
            raise HTTPException(status_code=500, detail="Failed to create project")
        # Return the inserted row
        inserted = res.data[0]
        return {
            "id": inserted["id"],
            "user_id": inserted["user_id"],
            "name": inserted["name"],
            "description": inserted.get("description"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str):
    sb = get_supabase()
    try:
        res = sb.table("projects").select("id,user_id,name,description").eq("id", project_id).single().execute()
        if not res.data:
            raise HTTPException(status_code=404, detail="Project not found")
        return res.data
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=list[ProjectOut])
def list_projects(user_id: str):
    sb = get_supabase()
    try:
        res = sb.table("projects").select("id,user_id,name,description").eq("user_id", user_id).order("created_at", desc=True).execute()
        return res.data or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
