from fastapi import APIRouter
from typing import Any, Dict

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/status")
def ml_status() -> Dict[str, Any]:
    from app.services.inference import get_inference_engine

    engine = get_inference_engine()
    return engine.status()
