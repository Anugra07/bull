# Datasets and Providers Documentation

This document provides a detailed overview of the datasets, data providers, and ML infrastructure used in the **Bull - Carbon Offset Land Analyzer**. The system uses a **cloud-native architecture** — GEE handles compute, FastAPI orchestrates, and Supabase stores results. No large rasters are downloaded locally.

## 1. Primary Data Providers

| Provider | Role | Key Datasets |
| :--- | :--- | :--- |
| **Google Earth Engine (GEE)** | **Compute & Data Platform** | Hosts and processes PB-scale geospatial datasets |
| **NASA** (USA) | **LIDAR & Fire Data** | GEDI (Biomass/Height), MODIS (Fire), SRTM (Elevation) |
| **ESA** (Europe) | **Optical & Radar** | Sentinel-2 (Vegetation), WorldCover (Land Cover), CCI (Biomass) |
| **Copernicus** (EU) | **Program** | Sentinel Mission (High-resolution optical imagery) |
| **UCSB / CHG** | **Climate Data** | CHIRPS (Rainfall/Precipitation) |
| **OpenLandMap** | **Soil Data** | Soil Organic Carbon, Bulk Density |
| **Woods Hole (WHRC)** | **Historical Baseline** | Pantropical Biomass (Legacy comparison) |
| **ORNL DAAC** | **Field Validation** | GEDI-FIA Fusion (Tabular Ground Truth) |

---

## 2. Detailed Dataset Breakdown

### 2.1. Biomass & Structure (LIDAR)

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **GEDI L4A Monthly AGBD** | `LARSE/GEDI/GEDI04_A_002_MONTHLY` | ~25m | Monthly | **Primary** Biomass. ML bias-corrected. |
| **GEDI L4A Annual AGBD** | `LARSE/GEDI/GEDI04_A_002` | ~25m | Annual | **Secondary** if monthly missing. |
| **GEDI L2A Canopy Height** | `LARSE/GEDI/GEDI02_A_002_MONTHLY` | ~25m | Monthly | Canopy Height (`rh98`). Allometric fallback. |
| **ESA CCI Biomass** | `ESA/CCI/BIOMASS/v4` | 100m | Annual | **Fallback** (Global) if GEDI = 0. |
| **WHRC Pantropical** | `WHRC/biomass/tropical` | 30m | Static | **Tertiary Fallback** (Tropics only). |

### 2.2. Vegetation & Optical Imagery

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **Sentinel-2 MSA/SR** | `COPERNICUS/S2_SR_HARMONIZED` | 10m / 20m | ~5 days | NDVI, EVI, trend analysis, QA/QC. |
| **ESA WorldCover** | `ESA/WorldCover/v200/2021` | 10m | Annual | Land Cover → Ecosystem type & risk factors. |

### 2.3. Soil (Geochemistry)

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **OpenLandMap SOC** | `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02` | 250m | Static | SOC content (g/kg) at 6 depths. |
| **OpenLandMap Bulk Density** | `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02` | 250m | Static | Bulk Density (kg/m³), converts SOC → t/ha. |

### 2.4. Climate & Weather

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **CHIRPS Daily** | `UCSB-CHG/CHIRPS/DAILY` | 5.5km | Daily | Rainfall, annual anomalies, drought risk. |

### 2.5. Terrain & Topography

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **NASADEM / SRTM** | `USGS/SRTMGL1_003` | 30m | Static | Elevation, Slope, Aspect. |

### 2.6. Fire & Disturbance

| Dataset Name | Earth Engine ID | Resolution | Frequency | Usage |
| :--- | :--- | :--- | :--- | :--- |
| **MODIS Burned Area** | `MODIS/006/MCD64A1` | 500m | Monthly | Fire scars, burned area %. |

---

## 3. ML Model Infrastructure (Phase 1)

### 3.1. Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌──────────────┐
│  Field Data CSVs │────▶│ Supabase         │────▶│ ML Training  │
│  (GEDI-FIA, etc) │     │ field_plots table │     │ Scripts      │
└─────────────────┘     └────────┬─────────┘     └──────┬───────┘
                                 │                       │
                    ┌────────────▼─────────┐    ┌────────▼───────┐
                    │ GEE Feature Extract  │    │ Trained Models │
                    │ (Sentinel-2, GEDI,   │    │ .pkl files     │
                    │  SRTM, CHIRPS)       │    └────────┬───────┘
                    └──────────────────────┘             │
                                                ┌───────▼────────┐
                                                │ carbon.py      │
                                                │ compute_carbon │
                                                └────────────────┘
```

### 3.2. Trained Models

| Model | Algorithm | Target | Training RMSE | R² | File |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **GEDI Bias Correction** | RandomForestRegressor | Biomass AGB (t/ha) | 19.48 t/ha | 0.968 | `backend/ml/models/gedi_bias_v1.pkl` |
| **SOC Downscaling** | GradientBoostingRegressor | SOC (tC/ha) | 14.68 tC/ha | 0.765 | `backend/ml/models/soc_downscaling_xgb_v1.pkl` |

### 3.3. Feature Vectors (GEE-Extracted)

Features extracted server-side via GEE for each field plot coordinate:

| Feature | Source Dataset | Description |
| :--- | :--- | :--- |
| `ndvi_mean` | Sentinel-2 | Median NDVI (±30 days from measurement) |
| `evi_mean` | Sentinel-2 | Median EVI |
| `gedi_agbd_raw` | GEDI L4A | Mean raw AGBD (±6 months) |
| `elevation` | SRTM | Elevation (m) |
| `slope` | SRTM | Terrain slope (°) |
| `aspect` | SRTM | Terrain aspect (°) |
| `rainfall_annual` | CHIRPS | Annual rainfall sum (mm) |

### 3.4. Ground Truth Data Sources

Tabular field data only (no raster downloads):

| Source | Type | Records | Fields |
| :--- | :--- | :--- | :--- |
| **GEDI-FIA Fusion** (ORNL DAAC) | CSV | Variable | Lat, Lon, AGB |
| **BioMassters** (Kaggle) | Labels CSV | ~13k | Lat, Lon, AGB |
| **China 30m AGB** (Zenodo) | Sample Points | Variable | Lat, Lon, AGB |

### 3.5. Database Schema (`field_plots`)

```sql
-- Supabase table for ground truth
field_plots (
  id UUID,
  dataset_name TEXT,        -- 'GEDI-FIA', 'BioMassters', etc.
  latitude FLOAT, longitude FLOAT,
  biomass_agb FLOAT,        -- t/ha
  biomass_bgb FLOAT,        -- t/ha (optional)
  soc_0_30cm FLOAT,         -- tC/ha
  ecosystem_type TEXT,
  climate_zone TEXT,
  features JSONB,           -- GEE-extracted feature vector
  created_at TIMESTAMPTZ
)
```

---

## 4. Data Integration Strategy

### 4.1. Biomass Estimation Hierarchy

1.  **GEDI L4A Monthly** → Mean AGBD + ML Bias Correction
2.  **GEDI L4A Annual** → Annual AGBD + ML Bias Correction
3.  **ESA CCI Biomass** → ESA CCI (2020)
4.  **Allometric Equations** → Canopy Height + Ecosystem Type
5.  **Zero/No Data** → Return 0 (manual review required)

### 4.2. Processing Pipeline

1.  **Input**: GeoJSON polygon
2.  **Geometry**: Centroid → Latitude/Climate Zone
3.  **Land Cover**: ESA WorldCover + Intelligent Snapping (latitude/NDVI context)
4.  **Carbon Stock**:
    *   **AGB**: GEDI/Fallback → **ML Bias Correction** (RandomForest)
    *   **BGB**: IPCC Root-to-Shoot ratios by ecosystem
    *   **SOC**: OpenLandMap layers → **ML Downscaling** (GradientBoosting)
5.  **Risk & Trend**: 5yr NDVI trend, MODIS fire, rainfall anomaly
6.  **QC**: Confidence Score (0-100), `ml_models_used` flag
7.  **MRV Baseline**: Additionality = Project CO₂ − Baseline CO₂

---

## 5. Cloud-Native Design Principles

| Principle | Implementation |
| :--- | :--- |
| **No local raster downloads** | All satellite data queried/processed on GEE servers |
| **Only download** | Small outputs, aggregated statistics, model-ready vectors |
| **GEE = Data + Compute** | Feature extraction, compositing, and reduction happen server-side |
| **FastAPI = Orchestrator** | Coordinates GEE calls, model inference, and API responses |
| **Supabase = Results Storage** | Stores field plots, analysis results, and user data |

---

## 6. Key Files

| File | Purpose |
| :--- | :--- |
| `backend/app/services/gee.py` | Core GEE data extraction (NDVI, Biomass, SOC, etc.) |
| `backend/app/services/features.py` | GEE feature extraction for ML training vectors |
| `backend/app/services/carbon.py` | Carbon computation + ML model integration |
| `backend/app/services/ecosystem.py` | Ecosystem classification and parameters |
| `backend/ml/train_gedi_bias.py` | GEDI bias correction training pipeline |
| `backend/ml/train_soc.py` | SOC downscaling training pipeline |
| `backend/scripts/ingest_field_data.py` | Field data ingestion to Supabase |
| `backend/migrations/create_field_plots_table.sql` | Database schema for ground truth |

---

## 7. References

*   **Sentinel-2**: [Copernicus Guide](https://sentinel.esa.int/web/sentinel/missions/sentinel-2)
*   **GEDI**: [NASA GEDI Mission](https://gedi.umd.edu/)
*   **ESA WorldCover**: [ESA WorldCover Product](https://esa-worldcover.org/en)
*   **OpenLandMap**: [OpenGeoHub](https://openlandmap.org/)
*   **CHIRPS**: [UCSB Climate Hazards Group](https://www.chc.ucsb.edu/data/chirps)
*   **ORNL DAAC**: [GEDI-FIA Fusion](https://daac.ornl.gov/)
*   **scikit-learn**: [sklearn Documentation](https://scikit-learn.org/stable/)
