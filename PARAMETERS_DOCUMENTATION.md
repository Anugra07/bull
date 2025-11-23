# Carbon Offset Land Analyzer - Parameters & Calculation Logic

## Overview
This document outlines all parameters, datasets, formulas, and calculation logic used in the analysis pipeline.

---

## 1. EARTH ENGINE (GEE) ANALYSIS PARAMETERS

### 1.1 Sentinel-2 Vegetation Indices (NDVI & EVI)

**Dataset**: `COPERNICUS/S2_SR` (Sentinel-2 Surface Reflectance)
- **Time Window**: `2023-01-01` to `2024-12-31` (2 years)
- **Cloud Filter**: < 20% cloudy pixels
- **Bands Selected**: `B1, B2, B3, B4, B5, B6, B7, B8, B8A, B9, B11, B12` (common spectral bands only)
- **Spatial Resolution**: 30 meters
- **Processing**: Median composite of all images in time range
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True (auto-adjusts resolution for large regions)

**Formulas**:
- **NDVI** = `(NIR - RED) / (NIR + RED)`
  - NIR = B8 band (scaled by dividing by 10000)
  - RED = B4 band (scaled by dividing by 10000)
  - Range: -1 to 1 (typically 0-1 for vegetation)
  
- **EVI** = `2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))`
  - NIR = B8 band
  - RED = B4 band
  - BLUE = B2 band
  - Range: -1 to 1 (better for dense vegetation)

**Calculation**: Mean value over the polygon

---

### 1.2 Canopy Height & Biomass

**Dataset**: `LARSE/GEDI/GEDI02_A_002_MONTHLY` (GEDI L2A Monthly)
- **Band**: `rh98` (98th percentile height)
- **Spatial Resolution**: 100 meters
- **Processing**: Median composite
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True

**Biomass Proxy**:
- **Formula**: `biomass = canopy_height * 10` (very rough placeholder)
- **Units**: t/ha (tonnes per hectare)
- **Note**: This is a placeholder. Real biomass should use calibrated models based on ecosystem type.

---

### 1.3 Soil Organic Carbon (SOC)

**Primary Dataset**: `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02`
- **Band**: `b0`
- **Spatial Resolution**: 250 meters
- **Units**: Percentage (%)
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True

**Fallback**: 
- If primary fails, tries: `projects/soilgrids-isric/clay_mean`
- **Default**: 2.0% if both fail

**Calculation**: Mean value over the polygon

---

### 1.4 Bulk Density

**Primary Dataset**: `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02`
- **Band**: `b0`
- **Spatial Resolution**: 250 meters
- **Units**: g/cm³ (grams per cubic centimeter)
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True

**Fallback**: 
- If primary fails, tries ImageCollection version
- **Default**: 1.3 g/cm³ if both fail

**Calculation**: Mean value over the polygon

---

### 1.5 Rainfall

**Dataset**: `UCSB-CHG/CHIRPS/DAILY` (Climate Hazards Group InfraRed Precipitation with Station data)
- **Time Window**: `2023-01-01` to `2023-12-31` (1 year)
- **Spatial Resolution**: 5000 meters (5 km)
- **Processing**: Sum of daily rainfall over the year
- **Units**: mm (millimeters)
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True

**Calculation**: Mean value over the polygon (total annual rainfall)

---

### 1.6 Elevation & Slope

**Dataset**: `USGS/SRTMGL1_003` (Shuttle Radar Topography Mission Global 1 arc-second)
- **Band**: `elevation`
- **Spatial Resolution**: 30 meters (~1 arc-second)
- **Slope Calculation**: `ee.Terrain.slope(elevation)`
- **Elevation Units**: meters above sea level
- **Slope Units**: degrees (°)
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True

**Calculation**: Mean value over the polygon

---

## 2. CARBON COMPUTATION PARAMETERS (`carbon.py`)

### 2.1 Default Risk Parameters

- **Fire Risk**: `0.05` (5% annual loss probability)
- **Drought Risk**: `0.03` (3% annual loss probability)
- **Trend Loss**: `0.02` (2% annual loss from other factors)
- **Total Risk**: `0.10` (10% combined risk factor)

### 2.2 IPCC Tier-1 Default Rate

- **Annual CO₂ Sequestration Rate**: `3.0 tCO₂e/ha/yr`
- **Note**: Conservative placeholder. Real rates vary by:
  - Ecosystem type (forest, grassland, wetland, etc.)
  - Climate zone
  - Management practices
  - Baseline conditions

### 2.3 Soil Depth Parameter

- **Soil Depth**: `0.30` meters (30 cm)
- **Note**: Standard depth for SOC calculations. Can be adjusted based on project type.

---

## 3. CARBON CALCULATION FORMULAS

### 3.1 Biomass Carbon

**Formula**: `carbon_biomass = biomass * 0.47`

Where:
- `biomass` = biomass in t/ha (from GEE analysis or proxy)
- `0.47` = carbon fraction in dry biomass (typical value)
- **Result**: `carbon_biomass` in tC/ha (tonnes of carbon per hectare)

**Note**: This is a proxy calculation. Real calculations should account for:
- Above-ground vs below-ground biomass
- Dead organic matter
- Species-specific carbon fractions

---

### 3.2 Soil Organic Carbon Total

**Formula**: `SOC_total = (SOC% / 100) * bulk_density * depth * area`

Where:
- `SOC%` = soil organic carbon percentage (from GEE)
- `bulk_density` = converted from g/cm³ to kg/m³ (multiply by 1000)
- `depth` = 0.30 meters (30 cm)
- `area` = polygon area in m²

**Step-by-step**:
1. `bulk_density_kg_m3 = bulk_density_g_cm3 * 1000`
2. `soc_fraction = soc_percent / 100`
3. `soc_kgC = soc_fraction * bulk_density_kg_m3 * depth_m * area_m2`
4. `soc_tC = soc_kgC / 1000` (convert to tonnes)

**Result**: `soc_total` in tC (tonnes of carbon)

---

### 3.3 Annual CO₂ Sequestration

**Formula**: `annual_co2 = annual_rate_tco2_ha_yr * area_ha`

Where:
- `annual_rate_tco2_ha_yr` = 3.0 tCO₂e/ha/yr (default IPCC Tier-1)
- `area_ha` = polygon area in hectares (m² / 10,000)

**Result**: `annual_co2` in tCO₂e/yr (tonnes of CO₂ equivalent per year)

---

### 3.4 20-Year CO₂ Projection

**Formula**: `co2_20yr = annual_co2 * 20`

Where:
- `annual_co2` = annual sequestration rate
- `20` = projection period in years

**Result**: `co2_20yr` in tCO₂e (tonnes of CO₂ equivalent over 20 years)

---

### 3.5 Risk-Adjusted CO₂

**Formula**: `risk_adjusted_co2 = co2_20yr * adjustment_factor`

Where:
- `adjustment_factor = max(0.0, 1.0 - fire_risk - drought_risk - trend_loss)`
- Minimum factor is 0.0 (prevents negative values)

**Example**:
- Fire risk: 5% (0.05)
- Drought risk: 3% (0.03)
- Trend loss: 2% (0.02)
- Adjustment factor: `1.0 - 0.05 - 0.03 - 0.02 = 0.90` (90%)

If `co2_20yr = 100 tCO₂e`, then:
- `risk_adjusted_co2 = 100 * 0.90 = 90 tCO₂e`

**Result**: `risk_adjusted_co2` in tCO₂e (conservative estimate accounting for risks)

---

## 4. CONVERSION FACTORS & CONSTANTS

### 4.1 Carbon to CO₂ Conversion

- **Molecular Weight Ratio**: CO₂/C = 44/12 ≈ 3.67
- **Note**: Currently not used in calculations. SOC stored as tC, not tCO₂e.

### 4.2 Area Conversions

- **Hectares to m²**: `1 ha = 10,000 m²`
- **m² to hectares**: `area_ha = area_m2 / 10,000`

### 4.3 Density Conversions

- **g/cm³ to kg/m³**: `bulk_density_kg_m3 = bulk_density_g_cm3 * 1000`

### 4.4 Biomass Carbon Fraction

- **Default**: `0.47` (47% carbon in dry biomass)
- **Range**: Typically 0.45-0.50 depending on species

---

## 5. DEFAULT VALUES & FALLBACKS

| Metric | Default Value | Used When |
|--------|--------------|-----------|
| SOC (%) | 2.0% | OpenLandMap datasets unavailable |
| Bulk Density | 1.3 g/cm³ | OpenLandMap datasets unavailable |
| Canopy Height | 0 m | GEDI data unavailable |
| Biomass | 0 t/ha | GEDI data unavailable |
| Rainfall | 0 mm | CHIRPS data unavailable |
| Elevation | 0 m | SRTM data unavailable |
| Slope | 0° | SRTM data unavailable |

---

## 6. USER-CONFIGURABLE PARAMETERS

These can be adjusted via the `/compute` endpoint:

- **fire_risk** (default: 0.05)
- **drought_risk** (default: 0.03)
- **trend_loss** (default: 0.02)
- **soil_depth_m** (default: 0.30) - currently hardcoded, can be made configurable

---

## 7. LIMITATIONS & NOTES

### 7.1 Placeholder Calculations

- **Biomass**: Very rough proxy (`canopy_height * 10`)
- **IPCC Rate**: Generic 3.0 tCO₂e/ha/yr (should be ecosystem-specific)
- **Carbon Fraction**: Fixed 0.47 (should vary by species)

### 7.2 Spatial Resolution Trade-offs

- **Sentinel-2**: 30m resolution (good for NDVI/EVI)
- **GEDI**: 100m resolution (coarser, but good for canopy height)
- **Soil Data**: 250m resolution (much coarser)
- **CHIRPS**: 5000m resolution (very coarse, but acceptable for annual rainfall)

### 7.3 Time Windows

- **Sentinel-2**: 2 years (2023-2024) - good for seasonal averages
- **CHIRPS**: 1 year (2023) - single year of rainfall
- **Other datasets**: No time filter (static datasets)

### 7.4 Missing Features (Future Enhancements)

- Ecosystem-specific sequestration rates
- Dynamic soil depth based on project type
- Better biomass models (allometric equations)
- Temporal trend analysis
- Land cover classification
- More sophisticated risk models

---

## 8. API ENDPOINTS

### 8.1 Analysis Endpoint
- **POST** `/analysis`
- **Input**: Polygon geometry or polygon_id
- **Output**: All 9 metrics (NDVI, EVI, biomass, canopy_height, SOC, bulk_density, rainfall, elevation, slope)

### 8.2 Compute Endpoint
- **POST** `/compute`
- **Input**: project_id, polygon_id, optional risk parameters
- **Output**: All metrics + carbon calculations (carbon_biomass, soc_total, annual_co2, co2_20yr, risk_adjusted_co2)
- **Stores**: Results in `project_results` table

---

## 9. DATA FLOW

```
Polygon Input
    ↓
[GEE Analysis]
    ├─→ Sentinel-2 → NDVI, EVI
    ├─→ GEDI → Canopy Height → Biomass (proxy)
    ├─→ OpenLandMap → SOC, Bulk Density
    ├─→ CHIRPS → Rainfall
    └─→ SRTM → Elevation, Slope
    ↓
[Metrics Dictionary]
    ↓
[Carbon Computation]
    ├─→ Biomass Carbon (biomass * 0.47)
    ├─→ SOC Total (SOC% * bulk_density * depth * area)
    ├─→ Annual CO₂ (rate * area)
    ├─→ 20-Year CO₂ (annual * 20)
    └─→ Risk-Adjusted CO₂ (20yr * adjustment_factor)
    ↓
[Results Stored in Database]
```

---

*Last Updated: Based on current codebase as of analysis*

