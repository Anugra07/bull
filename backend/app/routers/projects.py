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


@router.delete("/{project_id}")
def delete_project(project_id: str):
    sb = get_supabase()
    try:
        # Delete project - cascading delete should handle related polygons/results if configured in DB
        # If not, we might need to delete related data first, but usually DB handles this.
        res = sb.table("projects").delete().eq("id", project_id).execute()
        
        # Check if deletion was successful (Supabase returns the deleted rows)
        if not res.data:
             # It's possible the project didn't exist, or user didn't have permission
             # But for idempotency, we can just return success or 404 if strict
             raise HTTPException(status_code=404, detail="Project not found or could not be deleted")
             
        return {"message": "Project deleted successfully", "id": project_id}
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))
