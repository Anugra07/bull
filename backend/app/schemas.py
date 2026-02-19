from pydantic import BaseModel, Field, ConfigDict
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
    biomass: float  # Above-ground biomass (t/ha)
    biomass_aboveground: float | None = None
    biomass_belowground: float | None = None
    biomass_total: float | None = None
    biomass_source: str | None = None
    root_shoot_ratio: float | None = None
    canopy_height: float
    gedi_rh98: float | None = None
    canopy_cover: float | None = None
    gedi_quality_filtered: bool | None = None
    soc: float  # Total SOC in tC/ha for the selected depth
    soc_details: Optional[Dict[str, Any]] = None  # Detailed SOC info
    soil_depth_applied: str | None = None
    bulk_density: float
    rainfall: float
    rainfall_annual: float | None = None
    elevation: float
    slope: float
    aspect: float | None = None
    land_cover: float  # ESA WorldCover class code
    latitude: float | None = None
    longitude: float | None = None
    # Time-series trends (2020-2024, 5 years)
    ndvi_trend: float
    ndvi_trend_interpretation: str
    fire_burn_percent: float
    fire_recent_burn: bool
    rainfall_anomaly_percent: float
    trend_classification: str


class ComputeIn(BaseModel):
    project_id: str
    polygon_id: str
    fire_risk: float | None = None
    drought_risk: float | None = None
    trend_loss: float | None = None
    soil_depth: str = "0-30cm"  # "0-30cm", "0-100cm", "0-200cm"


class ComputeDirectIn(BaseModel):
    geometry: Any  # GeoJSON geometry/feature/featurecollection
    project_id: str | None = None
    fire_risk: float | None = None
    drought_risk: float | None = None
    trend_loss: float | None = None
    soil_depth: str = "0-30cm"

class ComputeOut(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    id: str
    project_id: str
    ndvi: float | None = None
    evi: float | None = None
    biomass: float | None = None
    biomass_aboveground: float | None = None
    biomass_belowground: float | None = None
    biomass_total: float | None = None
    biomass_source: str | None = None
    soc_source: str | None = None
    model_version_biomass: str | None = None
    model_version_soc: str | None = None
    ml_models_used: bool | None = None
    canopy_height: float | None = None
    soc: float | None = None
    soc_details: Optional[Dict[str, Any]] = None
    soil_depth_applied: str | None = None
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
    # Time-series trends
    ndvi_trend: float | None = None
    ndvi_trend_interpretation: str | None = None
    fire_burn_percent: float | None = None
    fire_recent_burn: bool | None = None
    rainfall_anomaly_percent: float | None = None
    trend_classification: str | None = None
    # QA/QC Metrics
    pixel_count: int | None = None
    ndvi_stddev: float | None = None
    soc_stddev: float | None = None
    rainfall_stddev: float | None = None
    cloud_coverage_percent: float | None = None
    gedi_shot_count: int | None = None
    data_confidence_score: float | None = None
    baseline_condition: str | None = None  # Overall baseline assessment
    
    # BASELINE Carbon Stock (MRV Compliance)
    baseline_biomass_carbon: float | None = None
    baseline_soc_total: float | None = None
    baseline_annual_co2: float | None = None
    baseline_co2_20yr: float | None = None
    baseline_scenario: str | None = None
    
    # PROJECT Carbon Stock (with intervention)
    project_annual_co2: float | None = None
    project_co2_20yr: float | None = None
    
    # ADDITIONALITY (Carbon Credits = Project - Baseline)
    additionality_annual_co2: float | None = None
    additionality_20yr: float | None = None

    # Prediction intervals (Phase 4 plumbing)
    prediction_interval_biomass_lower_95: float | None = None
    prediction_interval_biomass_upper_95: float | None = None
    prediction_interval_biomass_width: float | None = None
    prediction_interval_soc_lower_95: float | None = None
    prediction_interval_soc_upper_95: float | None = None
    prediction_interval_soc_width: float | None = None
