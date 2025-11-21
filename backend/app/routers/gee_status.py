from fastapi import APIRouter
from typing import Any, Dict
import os

from app.services.gee import init_gee, _GEE_ERR

router = APIRouter(prefix="/gee", tags=["gee"])

@router.get("/status")
def gee_status() -> Dict[str, Any]:
    ok = False
    err = None
    try:
        ok = init_gee()
    except Exception as e:
        err = str(e)
    return {
        "initialized": bool(ok),
        "error": err or _GEE_ERR,
        "env": {
            "GEE_SERVICE_ACCOUNT": bool(os.getenv("GEE_SERVICE_ACCOUNT")),
            "GEE_PRIVATE_KEY": bool(os.getenv("GEE_PRIVATE_KEY")),
            "GOOGLE_APPLICATION_CREDENTIALS": bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS")),
        },
    }
