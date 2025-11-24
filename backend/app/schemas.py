from pydantic import BaseModel, Field
from typing import Any, Optional, Dict

class ProjectCreate(BaseModel):
    user_id: str
    name: str = Field(min_length=1)
    description: Optional[str] = None

class ProjectOut(BaseModel):
    id: str
    user_id: str
    name: str
    description: Optional[str] = None

class PolygonIn(BaseModel):
    geometry: Any  # GeoJSON geometry or Feature

class PolygonCreate(PolygonIn):
    project_id: str

class PolygonOut(BaseModel):
    id: str
    project_id: str
    area_m2: float
    bbox: list[float]

class PolygonOutWithGeometry(PolygonOut):
    geometry: Any  # GeoJSON geometry


class AnalysisIn(BaseModel):
    polygon_id: Optional[str] = None
    geometry: Optional[Any] = None  # GeoJSON geometry or Feature
    soil_depth: str = "0-30cm"  # "0-30cm", "0-100cm", "0-200cm"

class AnalysisOut(BaseModel):
    ndvi: float
    evi: float
    biomass: float
    canopy_height: float
    soc: float  # Total SOC in tC/ha for the selected depth
    soc_details: Optional[Dict[str, Any]] = None  # Detailed SOC info
    bulk_density: float
    rainfall: float
    elevation: float
    slope: float
    land_cover: float  # ESA WorldCover class code


class ComputeIn(BaseModel):
    project_id: str
    polygon_id: str
    fire_risk: float | None = None
    drought_risk: float | None = None
    trend_loss: float | None = None
    soil_depth: str = "0-30cm"  # "0-30cm", "0-100cm", "0-200cm"

class ComputeOut(BaseModel):
    id: str
    project_id: str
    ndvi: float | None = None
    evi: float | None = None
    biomass: float | None = None
    canopy_height: float | None = None
    soc: float | None = None
    soc_details: Optional[Dict[str, Any]] = None
    bulk_density: float | None = None
    rainfall: float | None = None
    elevation: float | None = None
    slope: float | None = None
    land_cover: float | None = None  # ESA WorldCover class code
    ecosystem_type: str | None = None  # Ecosystem classification: Forest, Cropland, Grassland, etc.
    carbon_biomass: float | None = None
    soc_total: float | None = None
    annual_co2: float | None = None
    co2_20yr: float | None = None
    risk_adjusted_co2: float | None = None
