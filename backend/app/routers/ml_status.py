from fastapi import APIRouter
from typing import Any, Dict

from app.services.inference import get_inference_engine

router = APIRouter(prefix="/ml", tags=["ml"])


@router.get("/status")
def ml_status() -> Dict[str, Any]:
    engine = get_inference_engine()
    return engine.status()
