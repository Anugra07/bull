from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Load backend/.env explicitly
BASE_DIR = os.path.dirname(os.path.dirname(__file__))  # backend/
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

from app.routers.projects import router as projects_router
from app.routers.polygons import router as polygons_router
from app.routers.analysis import router as analysis_router
from app.routers.compute import router as compute_router
from app.routers.gee_status import router as gee_router

app = FastAPI(title="Carbon Offset Land Analyzer API", version="0.1.0")

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

# Routers
app.include_router(projects_router)
app.include_router(polygons_router)
app.include_router(analysis_router)
app.include_router(compute_router)
app.include_router(gee_router)
