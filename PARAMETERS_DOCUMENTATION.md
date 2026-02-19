# Carbon Offset Land Analyzer - Parameters, Methods, Models, and Data (Current Codebase)

## 1) Purpose and Scope
This document is the code-aligned technical reference for the current implementation in `/Users/anugragupta/Desktop/bull`.

It covers:
- What the backend computes today.
- Exact data sources used at runtime and in training scripts.
- Core formulas and routing logic.
- ML model loading/inference behavior in production.
- Public-data ingestion strategy (India-first, no personal IoT).
- Database schema surfaces relevant to analytics and ML.

Primary objective of the current system:
- Production analysis and carbon computation from polygon geometry.
- ML-assisted biomass/SOC inference in `/compute`.
- India-first optimization with open/public data policy.

## 2) High-Level Architecture
Backend API entrypoint:
- `/Users/anugragupta/Desktop/bull/backend/app/main.py`

Main API routes:
- `/health`
- `/gee/status`
- `/ml/status`
- `/analysis` (GEE metrics only)
- `/compute` (GEE + ML inference + carbon accounting + DB write)
- `/compute/direct` (GEE + ML inference + carbon accounting, no DB lookup/write requirement)

Core services:
- GEE extraction: `/Users/anugragupta/Desktop/bull/backend/app/services/gee.py`
- ML runtime inference engine: `/Users/anugragupta/Desktop/bull/backend/app/services/inference.py`
- Carbon accounting and risk/additionality math: `/Users/anugragupta/Desktop/bull/backend/app/services/carbon.py`
- Ecosystem classification/parameters: `/Users/anugragupta/Desktop/bull/backend/app/services/ecosystem.py`

## 3) Endpoint Behavior (Current)
### 3.1 `/analysis`
File: `/Users/anugragupta/Desktop/bull/backend/app/routers/analysis.py`

Flow:
1. Resolve geometry from payload geometry or `polygon_id`.
2. Call `analyze_polygon(geometry, soil_depth)`.
3. Return extracted metrics directly.

Important:
- `/analysis` does not run ML inference routing from `inference.py`.
- It returns GEE-derived values plus internal fallback/heuristic estimates in `gee.py`.

### 3.2 `/compute`
File: `/Users/anugragupta/Desktop/bull/backend/app/routers/compute.py`

Flow:
1. Load polygon geometry + area from Supabase (`project_polygons`).
2. Run GEE analysis (`analyze_polygon`).
3. Run production inference (`get_inference_engine().predict(metrics)`).
4. Run carbon computation (`compute_carbon(..., apply_ml=False)`) to avoid double ML application.
5. Persist into `project_results`.

Resilience behavior:
- Insert fallback removes unknown columns on `PGRST204` schema-cache mismatch and retries (`_insert_project_result_with_fallback`).

### 3.3 `/compute/direct`
File: `/Users/anugragupta/Desktop/bull/backend/app/routers/compute.py`

Flow:
- Same compute stack as `/compute` but bypasses Supabase polygon lookup and write path.
- Useful for local/live validation with raw geometry.

### 3.4 `/ml/status`
File: `/Users/anugragupta/Desktop/bull/backend/app/routers/ml_status.py`

Returns runtime readiness and metadata for:
- `gedi_bias`
- `soc_downscaling`
- `stocking_index`

Includes:
- model path, exists/ready flags, version, trained_at, RMSE/R² when available, feature list.

## 4) Runtime Data Sources (GEE and Geospatial)
Primary extraction implementation:
- `/Users/anugragupta/Desktop/bull/backend/app/services/gee.py`

### 4.1 Vegetation Indices
Dataset:
- `COPERNICUS/S2_SR_HARMONIZED`

Processing:
- Date window: 2023-01-01 to 2024-12-31 for base metrics.
- SCL cloud mask (keep classes 4/5/6).
- Composite preference: dry season (Nov-Apr), fallback wet season.

Formulas:
- `NDVI = (NIR - RED) / (NIR + RED)` using `B8`, `B4`.
- `EVI = 2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))` using `B8`, `B4`, `B2`.

### 4.2 Biomass and Height
Datasets:
- GEDI L2A canopy height: `LARSE/GEDI/GEDI02_A_002_MONTHLY` (`rh98`)
- GEDI L4A biomass monthly: `LARSE/GEDI/GEDI04_A_002_MONTHLY` (`agbd`)
- GEDI L4A biomass annual fallback: `LARSE/GEDI/GEDI04_A_002` (`agbd`)
- Additional fallback layers:
  - `ESA/CCI/BIOMASS/v4`
  - `WHRC/biomass/tropical`

Logic:
1. Prefer GEDI monthly AGBD.
2. Fallback GEDI annual AGBD.
3. Fallback ESA CCI biomass.
4. Fallback WHRC tropical biomass.
5. Final fallback allometric equations from canopy height and land-cover class.

Pre-ML heuristic correction in `gee.py`:
- GEDI forest values get latitude/biomass-tier correction multipliers.
- Note: production `/compute` then applies ML routing in `inference.py`, which is the final inference layer for compute outputs.

### 4.3 Below-Ground Biomass
Root:shoot ratios in `gee.py` (IPCC-style rules) by class/latitude, including:
- tropical forest 0.24, temperate 0.29, boreal 0.32,
- shrubland 0.40,
- mangrove 0.39,
- grassland 3.0.

Computed fields:
- `biomass_aboveground` (AGB)
- `biomass_belowground` (BGB)
- `biomass_total = AGB + BGB`

### 4.4 Soil Organic Carbon and Bulk Density
Datasets:
- SOC: `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02`
- Bulk density: `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02`

Depth options:
- `0-30cm`, `0-100cm`, `0-200cm`

Layer-sum formulation in code:
- For each layer included by selected depth:
- `SOC_layer_tC_ha = 0.1 * BD(g/cm3) * SOC(g/kg) * thickness(cm)`
- Total SOC is sum of selected layers.

Outputs:
- `soc` (tC/ha at selected depth)
- `soc_details` (method and metadata)
- `soil_depth_applied`
- representative `bulk_density`

### 4.5 Climate and Terrain
Datasets:
- Rainfall: `UCSB-CHG/CHIRPS/DAILY`
- Elevation: `USGS/SRTMGL1_003`
- Land cover: `ESA/WorldCover/v200/2021`

Derived:
- rainfall annual sum (`rainfall`, `rainfall_annual`)
- elevation, slope, aspect
- `land_cover` class
- centroid latitude/longitude

### 4.6 Trend and QA Metrics
Trend stack in `gee.py`:
- NDVI yearly trend (2020-2024) via linear slope.
- Burned area and recent burn from `MODIS/006/MCD64A1`.
- Rainfall anomaly (%): recent 5-year mean vs long-term 25-year mean from CHIRPS.

Trend classification:
- `Degrading`, `Fire-Impacted`, `Drought-Stressed`, `Improving/Regenerating`, `Recovering`, `Stable`.

QA fields:
- `pixel_count`, `ndvi_stddev`, `soc_stddev`, `rainfall_stddev`,
- `cloud_coverage_percent`, `gedi_shot_count`, `data_confidence_score`.

## 5) Production ML Inference (What Actually Drives `/compute`)
Core engine:
- `/Users/anugragupta/Desktop/bull/backend/app/services/inference.py`

### 5.1 Model Artifacts
Directory:
- `/Users/anugragupta/Desktop/bull/backend/ml/models`

Expected artifacts:
- `gedi_bias_v1.pkl` + `gedi_bias_v1.meta.json`
- `soc_downscaling_xgb_v1.pkl` + `soc_downscaling_xgb_v1.meta.json`
- `stocking_index_calibrated_v1.pkl` + `stocking_index_calibrated_v1.meta.json`

### 5.2 Routing Logic
Biomass routing order:
1. Ecosystem-specific SI model if matching key exists (`stocking_index_calibrated_v1`).
2. GEDI bias RF model (`gedi_bias_v1`).
3. Raw GEE biomass fallback.

SOC routing:
1. SOC model (`soc_downscaling_xgb_v1`).
2. Raw GEE SOC fallback.

Ecosystem label mapping for SI routing uses `land_cover` + latitude.

### 5.3 Deterministic Feature Alignment
`InferenceEngine` aligns runtime features to model schema using:
- `feature_names_in_` when available, else metadata feature list.
- explicit one-hot filling for `ecosystem_*` and `climate_zone_*` columns.
- missing features default to 0.0.

### 5.4 Prediction Intervals
Biomass intervals:
- If model has `estimators_` (RF), compute tree-level distribution and take 2.5/97.5 percentiles.

SOC intervals:
- RMSE-based approximation: `mean ± 1.96 * rmse` (floored at 0 lower bound).

Returned by inference engine:
- `biomass_interval`, `soc_interval`, `ml_models_used`, sources, model versions.

## 6) Carbon Accounting Logic
Implementation:
- `/Users/anugragupta/Desktop/bull/backend/app/services/carbon.py`

### 6.1 Core Carbon Formulas
Inputs:
- `biomass_total` (preferred), `soc` (tC/ha), polygon area.

Formulas:
- Biomass carbon fraction: `C_biomass = biomass_total * 0.47` (tC/ha).
- `area_ha = area_m2 / 10000`.
- `soc_total = soc_tC_ha * area_ha` (tC total).
- `annual_co2 = sequestration_rate_tCO2e_ha_yr * area_ha`.
- `co2_20yr = annual_co2 * 20`.

### 6.2 Risk Adjustment
Default ecosystem risks + optional overrides:
- fire risk, drought risk, trend loss.

Trend-aware adjustments from metrics:
- Increase penalties for recent burn, high burn %, severe rainfall anomaly, degrading NDVI trend.

Final:
- `adj_factor = max(0, 1 - fire_risk - drought_risk - trend_loss)`
- `risk_adjusted_co2 = co2_20yr * adj_factor`

### 6.3 Baseline, Project, Additionality
Baseline scenario determined from trend condition.

Outputs include:
- baseline biomass/SOC/annual/20-year,
- project annual/20-year,
- additionality annual/20-year (clipped non-negative).

## 7) Ecosystem Classification and Parameters
Implementation:
- `/Users/anugragupta/Desktop/bull/backend/app/services/ecosystem.py`

Based on ESA WorldCover class.

Forest sequestration rates are climate/rainfall dependent:
- Boreal (`|lat| > 55`): 3.0
- Temperate (`23.5 < |lat| <= 55`): 11.0
- Tropical with rainfall > 1400mm: 17.5
- Tropical otherwise: 5.0

Non-forest defaults exist for Mangrove, Cropland, Grassland, Wetland, Shrubland, Plantation, Degraded, Other.

## 8) Training Pipelines (Current Scripts)
### 8.1 GEDI Bias Model
Script:
- `/Users/anugragupta/Desktop/bull/backend/ml/train_gedi_bias.py`

Model:
- `RandomForestRegressor`.

Features used:
- GEDI raw AGB, NDVI/EVI means, elevation, slope, rainfall annual, latitude, ecosystem/climate one-hot.

Data source:
- `field_plots` with populated `features`; falls back to mock if insufficient data.

### 8.2 SOC Model
Script:
- `/Users/anugragupta/Desktop/bull/backend/ml/train_soc.py`

Model:
- `GradientBoostingRegressor` (saved under `soc_downscaling_xgb_v1.pkl` name for compatibility).

Features used:
- NDVI/EVI, elevation, slope, aspect, rainfall annual, lat/lon, ecosystem one-hot.

Data source:
- `field_plots.soc_0_30cm` + features; mock fallback if insufficient.

### 8.3 Stocking Index Calibration Models
Script:
- `/Users/anugragupta/Desktop/bull/backend/ml/train_si_calibration.py`

Model family:
- Ecosystem-specific `RandomForestRegressor` models.

Features:
- `ndvi`, `evi`, `gedi_rh98`, `canopy_cover`, `elevation`, `slope`, `rainfall_annual`.

Data source:
- `verra_monitoring_data` (plot_data + gee_features), with synthetic fallback when needed.

### 8.4 Metadata and Reproducibility
Training scripts write `.meta.json` with:
- version, timestamp, sample count, RMSE, R², feature names,
- policy tag `open_public_no_personal_iot`, geo scope `india_first`.

## 9) Public Data Ingestion (India-First, No Personal IoT)
### 9.1 Policy
Policy tag:
- `open_public_no_personal_iot`

Script policy enforcement:
- `/Users/anugragupta/Desktop/bull/backend/scripts/ingest_field_data.py`

Approved source keys currently:
- `gedi-fia`
- `china-agb`
- `biomassters`

### 9.2 Extract-Only Strategy for Large Datasets
Implemented tools:
- `/Users/anugragupta/Desktop/bull/backend/scripts/extract_remote_public_data.py`
- `/Users/anugragupta/Desktop/bull/backend/scripts/ingest_field_data.py`
- `/Users/anugragupta/Desktop/bull/backend/scripts/backfill_field_plot_features.py`
- `/Users/anugragupta/Desktop/bull/backend/EXTRACTION_STRATEGY.md`

Key behavior:
- Stream large remote files in chunks.
- Keep minimal columns.
- India-only filter by default.
- Backfill per-plot GEE features without raster downloads.

## 10) Verra Data Pipeline
Scripts:
- `/Users/anugragupta/Desktop/bull/backend/scripts/scrape_verra.py`
- `/Users/anugragupta/Desktop/bull/backend/scripts/parse_monitoring_reports.py`

What is implemented:
- Scrape/save project metadata and monitoring-report URLs.
- Parse PDFs for SI type, R², equations, benchmark hints, carbon stock snippets, plot table hints.
- Batch process reports and optionally enrich with GEE features before saving.

Tables:
- `verra_projects`
- `verra_monitoring_data`

## 11) Database Schema Surfaces
Baseline migration:
- `/Users/anugragupta/Desktop/bull/supabase/migrations/20251122003108_initial_schema.sql`

India ML/Verra migration:
- `/Users/anugragupta/Desktop/bull/supabase/migrations/20260219124500_india_ml_verra_schema.sql`

Key tables used by current backend:
- `projects`
- `project_polygons`
- `project_results`
- `field_plots`
- `verra_projects`
- `verra_monitoring_data`

`project_results` now includes:
- trend/QA metrics,
- baseline/project/additionality fields,
- ML source/version flags,
- biomass components,
- prediction interval fields,
- `soil_depth_applied`.

## 12) Current Known Gaps / Practical Notes
1. `/analysis` is GEE-centric and does not apply inference routing; `/compute` is the production ML path.
2. GEE service contains both strong extraction logic and some heuristic fallbacks; compute path relies on inference models to standardize final outputs.
3. SOC interval uses RMSE approximation; not yet conformal/quantile calibration.
4. Verra parsing quality depends on report formatting and registry page structure.
5. Some training scripts still allow synthetic fallback when DB data is insufficient.

## 13) Validation and Tests Added
Tests:
- `/Users/anugragupta/Desktop/bull/backend/tests/test_inference_engine.py`
- `/Users/anugragupta/Desktop/bull/backend/tests/test_ingest_policy.py`

Coverage includes:
- deterministic feature-order and one-hot alignment,
- fallback behavior when model artifacts are absent,
- policy enforcement against non-approved data source keys,
- India-only filtering behavior in record construction.

Run:
```bash
cd /Users/anugragupta/Desktop/bull/backend
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
```

## 14) Operational Runbook (Current)
Start backend:
```bash
cd /Users/anugragupta/Desktop/bull/backend
.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Check health:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/gee/status
curl http://localhost:8000/ml/status
```

Direct compute smoke test:
```bash
curl -X POST http://localhost:8000/compute/direct \
  -H 'Content-Type: application/json' \
  -d '{
    "project_id":"direct-test",
    "geometry":{"type":"Polygon","coordinates":[[[77.58,12.97],[77.60,12.97],[77.60,12.99],[77.58,12.99],[77.58,12.97]]]},
    "soil_depth":"0-30cm"
  }'
```

Supabase migrations:
```bash
cd /Users/anugragupta/Desktop/bull
supabase db push
```
Then in SQL editor:
```sql
NOTIFY pgrst, 'reload schema';
```

---
If this document is updated, it should be updated only with behavior verified in code under `/Users/anugragupta/Desktop/bull/backend` and active migrations under `/Users/anugragupta/Desktop/bull/supabase/migrations`.
