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

**Canopy Height Dataset**: `LARSE/GEDI/GEDI02_A_002_MONTHLY` (GEDI L2A Monthly)
- **Band**: `rh98` (98th percentile height)
- **Spatial Resolution**: 100 meters
- **Processing**: Median composite

**Biomass Calculation (Priority Order)**:

1.  **Primary**: `LARSE/GEDI/GEDI04_A_002_MONTHLY` (GEDI L4A Monthly AGBD)
    -   **Band**: `agbd` (Above Ground Biomass Density)
    -   **Units**: Mg/ha (t/ha)
    -   **Resolution**: 100m (aggregated from 25m footprints)

2.  **Secondary**: `LARSE/GEDI/GEDI04_A_002` (GEDI L4A Annual AGBD)
    -   Used if monthly data is unavailable.

3.  **Fallback**: Allometric Equations (if GEDI AGBD is unavailable)
    -   Based on **Canopy Height** (`rh98`) and **Ecosystem Type** (ESA WorldCover).
    -   **Forest/Mangroves**: `15 * h + 2 * h^1.5`
    -   **Shrubland**: `8 * h + 1.5 * h^1.3`
    -   **Grassland**: `3 * h`
    -   **Cropland**: `5 * h`
    -   **Default**: `10 * h + 2 * h^1.5`

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

### 1.7 Land Cover & Ecosystem Classification

**Dataset**: `ESA/WorldCover/v200/2021`
- **Resolution**: 10m
- **Processing**: Mode (most frequent class) over polygon

**Classification Logic**:

| Class | Name | Ecosystem Type |
| :--- | :--- | :--- |
| 10 | Tree cover | **Forest** (or Plantation) |
| 20 | Shrubland | **Shrubland** |
| 30 | Grassland | **Grassland** |
| 40 | Cropland | **Cropland** |
| 50 | Built-up | **Other** |
| 60 | Bare / sparse | **Degraded** |
| 70 | Snow and ice | **Other** |
| 80 | Permanent water | **Wetland** |
| 90 | Herbaceous wetland | **Wetland** |
| 95 | Mangroves | **Wetland** (prioritized over Forest) |
| 100 | Moss and lichen | **Other** |

---

## 2. CARBON COMPUTATION PARAMETERS

### 2.1 Ecosystem-Specific Parameters

Carbon sequestration rates and risk factors are determined by the Ecosystem Type identified above.

### 3.2 Annual CO2 Sequestration Rates

**Climate-Specific Forest Rates (IPCC-Based)**:
- **Boreal Forests** (latitude > 55°): **3.0 tCO2e/ha/yr**
  - IPCC Range: 1.5-4.4 tCO2e/ha/yr
  - Applies to: Canada, Scandinavia, Russia
  
- **Temperate Forests** (23.5° < latitude ≤ 55°): **11.0 tCO2e/ha/yr**
  - IPCC Range: 5.5-16.5 tCO2e/ha/yr
  - Applies to: USA, Europe, China, Japan
  
- **Tropical Forests** (latitude ≤ 23.5°): **22.0 tCO2e/ha/yr**
  - IPCC Range: 14.7-29.4 tCO2e/ha/yr
  - Applies to: Amazon, Congo, Southeast Asia

**Other Ecosystems** (Fixed Rates):
- **Mangrove**: 10.0 tCO2e/ha/yr (IPCC: 8-12)
- **Cropland**: 0.8 tCO2e/ha/yr (agricultural soils)
- **Grassland**: 1.5 tCO2e/ha/yr (improved management)
- **Wetland**: 4.0 tCO2e/ha/yr (peatlands/wetlands)
- **Shrubland**: 2.0 tCO2e/ha/yr
- **Plantation**: 6.0 tCO2e/ha/yr (managed plantations)
- **Degraded**: 0.3 tCO2e/ha/yr
- **Other**: 0.0 tCO2e/ha/yr

**Source**: IPCC Special Report on Land Use, IPCC 2006 Guidelines Vol 4

**Implementation**: 
- Latitude is calculated from polygon centroid
- Forest sequestration rate is automatically adjusted based on climate zone
- Ensures IPCC compliance and maximum accuracy

| Ecosystem | Fire Risk | Drought Risk | Trend Loss |
| :--- | :--- | :--- | :--- |
| **Forest** | 0.08 | 0.04 | 0.02 |
| **Mangrove** | 0.01 | 0.05 | 0.03 |
| **Wetland** | 0.01 | 0.08 | 0.04 |
| **Grassland** | 0.05 | 0.05 | 0.02 |
| **Shrubland** | 0.06 | 0.05 | 0.02 |
| **Cropland** | 0.02 | 0.06 | 0.03 |
| **Plantation** | 0.07 | 0.03 | 0.01 |
| **Degraded** | 0.03 | 0.07 | 0.05 |
| **Other** | 0.01 | 0.01 | 0.01 |

### 2.2 Soil Depth Parameter

- **Soil Depth**: `0.30` meters (30 cm)
- **Note**: Standard depth for SOC calculations.

---

## 3. CARBON CALCULATION FORMULAS

### 3.1 Biomass Carbon

**Formula**: `carbon_biomass = biomass * 0.47`

Where:
- `biomass` = biomass in t/ha (from GEDI L4A or allometric fallback)
- `0.47` = carbon fraction in dry biomass (typical value)
- **Result**: `carbon_biomass` in tC/ha (tonnes of carbon per hectare)

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
- `annual_rate_tco2_ha_yr` = Ecosystem-specific rate (see table 2.1)
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
- Risk factors are ecosystem-specific (see table 2.1) unless overridden by user.

**Example (Forest)**:
- Fire risk: 0.08
- Drought risk: 0.04
- Trend loss: 0.02
- Adjustment factor: `1.0 - 0.08 - 0.04 - 0.02 = 0.86`
- `risk_adjusted_co2 = co2_20yr * 0.86`

**Result**: `risk_adjusted_co2` in tCO₂e

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

---

## 5. API ENDPOINTS

### 5.1 Analysis Endpoint
- **POST** `/analysis`
- **Input**: Polygon geometry or polygon_id
- **Output**: All 9 metrics (NDVI, EVI, biomass, canopy_height, SOC, bulk_density, rainfall, elevation, slope)

### 5.2 Compute Endpoint
- **POST** `/compute`
- **Input**: project_id, polygon_id, optional risk parameters
- **Output**: All metrics + carbon calculations (carbon_biomass, soc_total, annual_co2, co2_20yr, risk_adjusted_co2)
- **Stores**: Results in `project_results` table

---

## 6. DATA FLOW

```
Polygon Input
    ↓
[GEE Analysis]
    ├─→ Sentinel-2 → NDVI, EVI
    ├─→ GEDI L4A (or L2A + Allometric) → Biomass
    ├─→ OpenLandMap → SOC, Bulk Density
    ├─→ CHIRPS → Rainfall
    ├─→ SRTM → Elevation, Slope
    └─→ ESA WorldCover → Land Cover Class
    ↓
[Metrics Dictionary]
    ↓
[Ecosystem Classification]
    └─→ Land Cover Class → Ecosystem Type (Forest, Wetland, etc.)
    ↓
[Carbon Computation]
    ├─→ Biomass Carbon (biomass * 0.47)
    ├─→ SOC Total (SOC% * bulk_density * depth * area)
    ├─→ Annual CO₂ (Ecosystem Rate * area)
    ├─→ 20-Year CO₂ (annual * 20)
    └─→ Risk-Adjusted CO₂ (20yr * (1 - risks))
    ↓
[Results Stored in Database]
```
