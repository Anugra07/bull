# Carbon Offset Land Analyzer - Methodology & Technical Documentation

## Overview
This document serves as the **Single Source of Truth** for the scientific methodology, algorithms, and data sources used in the Carbon Offset Land Analyzer. It details how we extract satellite data, calculate carbon stocks, determine additionality, and where the current limitations lie compared to on-the-ground verification standards (e.g., Verra, Gold Standard).

---

## 1. DATA EXTRACTION (Google Earth Engine)

### 1.1 Sentinel-2 Vegetation Indices (NDVI & EVI)

**Dataset**: `COPERNICUS/S2_SR_HARMONIZED` (Sentinel-2 Surface Reflectance - Harmonized)
- **Time Window**: `2023-01-01` to `2024-12-31` (2 years)
- **Cloud Filtering**: 
  - Metadata filter: < 30% cloudy pixels
  - **SCL (Scene Classification Layer) Masking**: Pixel-level cloud removal
    - Keeps: Vegetation (4), Bare soil (5), Water (6)
    - Masks: Clouds (8,9), Shadows (3), Cirrus (10), Snow (11)
- **Bands**: B2 (Blue), B4 (Red), B8 (NIR), B11, B12
- **Spatial Resolution**: **10 meters** (B2, B3, B4, B8 are native 10m resolution)
- **Processing**: 
  - **Seasonal Composites**: Dry season (Nov-Apr) and Wet season (May-Oct)
  - Uses dry season median (better for vegetation, less cloud)
  - Falls back to wet season if dry has no data
- **Max Pixels**: 1 billion (1e9)
- **Best Effort**: True (auto-adjusts for large regions)

**Cloud Masking Function**:
```python
def mask_s2_clouds(image):
    scl = image.select('SCL')
    # Keep only clear pixels (4=vegetation, 5=not_vegetated, 6=water)
    mask = scl.eq(4).Or(scl.eq(5)).Or(scl.eq(6))
    return image.updateMask(mask)
```

**NDVI Formula**: `NDVI = (NIR - RED) / (NIR + RED)`
- NIR = B8 band / 10000 (Sentinel-2 SR is scaled 0-10000)
- RED = B4 band / 10000
- **Purpose**: Proxy for vegetation health and density.
- Range: -1 to 1 (typically 0-1 for vegetation)
- Higher values indicate healthier/denser vegetation

**EVI Formula**: `EVI = 2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))`
- Coefficients: G=2.5, C1=6.0, C2=7.5, L=1
- **Purpose**: Corrects for soil background signals and atmospheric influences. Better for high biomass regions (e.g., rainforests) where NDVI saturates.

**Calculation**: Mean value over polygon at 10m resolution

---

### 1.2 Canopy Height & Biomass

**Canopy Height Dataset**: `LARSE/GEDI/GEDI02_A_002_MONTHLY`
- **Product**: GEDI L2A Monthly (Canopy Height)
- **Band**: `rh98` (98th percentile relative height)
- **Spatial Resolution**: 100 meters (aggregated from 25m footprints)
- **Processing**: Median composite
- **Units**: meters (m)

**Biomass Calculation (3-tier Priority)**:

**Tier 1 (Primary)**: `LARSE/GEDI/GEDI04_A_002_MONTHLY`
- Product: GEDI L4A Monthly AGBD
- Band: `agbd` (Above Ground Biomass Density)
- Units: Mg/ha (tonnes/hectare)
- Resolution: 100m
- Processing: Mean over polygon
- **NEW: Bias Correction Applied** (see below)

**Tier 2 (Fallback)**: `LARSE/GEDI/GEDI04_A_002`
- Product: GEDI L4A Annual AGBD
- Used if monthly data unavailable
- **NEW: Bias Correction Applied** (see below)

**Tier 3 (Allometric Equations)**:
Used if GEDI AGBD unavailable. Based on canopy height and ecosystem:

```python
# Forest & Mangroves
biomass = 15 * height + 2 * (height ** 1.5)

# Shrubland
biomass = 8 * height + 1.5 * (height ** 1.3)

# Grassland
biomass = 3 * height

# Cropland
biomass = 5 * height

# Default
biomass = 10 * height + 2 * (height ** 1.5)
```

#### GEDI Bias Correction (NEW - Production Upgrade)

Research shows GEDI L4A systematically underestimates biomass by **-31.65 Mg/ha** on average, with errors ranging from 19% to 50% across sites. We apply ecosystem-specific correction factors:

```python
def apply_gedi_bias_correction(raw_biomass, ecosystem, latitude):
    if ecosystem != "Forest":
        return raw_biomass  # No correction for non-forest
    
    abs_lat = abs(latitude)
    if abs_lat <= 23.5:  # Tropical
        if raw_biomass > 250:
            correction_factor = 1.35  # +35% for very high density
        elif raw_biomass > 150:
            correction_factor = 1.25  # +25% for high density
        else:
            correction_factor = 1.15  # +15% for moderate density
    elif abs_lat <= 55:  # Temperate
        if raw_biomass > 200:
            correction_factor = 1.20  # +20% for high density
        else:
            correction_factor = 1.10  # +10% for moderate density
    else:  # Boreal
        correction_factor = 1.10  # +10%
    
    return raw_biomass * correction_factor
```

**Correction Factors by Ecosystem**:
| Ecosystem | Biomass Range | Correction | Rationale |
|-----------|---------------|------------|-----------|
| Tropical Forest | >250 Mg/ha | +35% | Highest underestimation in dense rainforests |
| Tropical Forest | 150-250 Mg/ha | +25% | Moderate underestimation |
| Tropical Forest | <150 Mg/ha | +15% | Lower underestimation |
| Temperate Forest | >200 Mg/ha | +20% | Dense temperate forests |
| Temperate Forest | <200 Mg/ha | +10% | Moderate temperate forests |
| Boreal Forest | All | +10% | Minimal underestimation |

**Source**: Taylor & Francis (2023), Frontiers in Remote Sensing (2022)

#### Belowground Biomass (BGB) - NEW

**CRITICAL ADDITION**: The original model only calculated Above-Ground Biomass (AGB). Roots store **20-40% of total plant carbon** and MUST be included for accurate carbon accounting.

**IPCC 2019 Root-to-Shoot (R:S) Ratios**:

```python
ROOT_SHOOT_RATIOS = {
    'tropical': 0.24,      # Tropical forests
    'temperate': 0.29,     # Temperate forests
    'boreal': 0.32,        # Boreal forests
    'grassland': 3.0,      # CRITICAL: Grasslands store most carbon in roots!
    'shrubland': 0.40,     # Shrublands
    'mangrove': 0.39       # Mangrove forests
}

# Calculate BGB
BGB = AGB * root_shoot_ratio
Total_Biomass = AGB + BGB
```

**Impact by Ecosystem**:
| Ecosystem | R:S Ratio | Example AGB | BGB | Total | Increase |
|-----------|-----------|-------------|-----|-------|----------|
| Tropical Forest | 0.24 | 300 t/ha | 72 t/ha | 372 t/ha | +24% |
| Temperate Forest | 0.29 | 200 t/ha | 58 t/ha | 258 t/ha | +29% |
| Boreal Forest | 0.32 | 150 t/ha | 48 t/ha | 198 t/ha | +32% |
| **Grassland** | **3.0** | 10 t/ha | **30 t/ha** | **40 t/ha** | **+300%** |
| Mangrove | 0.39 | 250 t/ha | 97.5 t/ha | 347.5 t/ha | +39% |

**Source**: IPCC 2019 Refinement to 2006 Guidelines, Copernicus Global Carbon Budget

**Result**: 
- `biomass_aboveground` (AGB) in t/ha
- `biomass_belowground` (BGB) in t/ha  
- `biomass_total` (AGB + BGB) in t/ha

---

### 1.3 Soil Organic Carbon (SOC) - Depth-Specific

**Dataset**: `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02`
- **Depth Layers**:
  - `b0`: 0-5 cm
  - `b10`: 5-15 cm
  - `b30`: 15-30 cm
  - `b60`: 30-60 cm
  - `b100`: 60-100 cm
  - `b200`: 100-200 cm
- **Spatial Resolution**: 250 meters
- **Units**: g/kg (grams of carbon per kilogram of soil)
- **Processing**: Mean over polygon for each layer

**SOC Calculation by Depth** (user-selectable):

**Option 1: 0-30cm (Standard)**
```python
# Layer thicknesses in meters
layers = [
    ('b0', 0.05),   # 0-5cm
    ('b10', 0.10),  # 5-15cm  
    ('b30', 0.15)   # 15-30cm
]

total_soc = 0
for band, thickness in layers:
    soc_layer = soc_image.select(band)  # g/kg
    bd_layer = bulk_density.select(band)  # g/cm³
    
    # Calculate carbon for this layer (tC/ha)
    # BD (g/cm³) * 0.01 = BD in kg/m³ / 100
    # SOC (g/kg) is already a fraction
    layer_carbon = bd_layer * 0.01 * soc_layer * thickness * 0.1
    total_soc += layer_carbon

# Result: tC/ha (tonnes of carbon per hectare)
```

**Option 2: 0-100cm (Deep)**
Uses all 6 layers (b0, b10, b30, b60, b100, b200)

**Depth Options**:
- `0-30cm`: Standard for most carbon accounting (default)
- `0-100cm`: Deep soil carbon analysis

---

### 1.4 Bulk Density (Depth-Specific)

**Dataset**: `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02`
- **Depth Layers**: Same as SOC (b0, b10, b30, b60, b100, b200)
- **Spatial Resolution**: 250 meters
- **Units**: kg/dm³ (raw values need conversion)
- **Conversion**: Multiply by 0.01 to get g/cm³
- **Fallback**: 1.3 g/cm³ if data unavailable
- **Processing**: Mean over polygon for each layer

---

### 1.5 Rainfall (Annual & Anomaly Analysis)

**Dataset**: `UCSB-CHG/CHIRPS/DAILY` (Climate Hazards Group)
- **Band**: `precipitation`
- **Spatial Resolution**: 5000 meters (5 km)
- **Units**: mm/day
- **Processing**: 
  - **Annual**: Sum over 1 year (2023-01-01 to 2023-12-31)
  - **Long-term mean**: 25-year average (1999-2024)
  - **Recent mean**: 5-year average (2020-2024)

**Rainfall Anomaly Calculation**:
```python
# Calculate anomaly percentage
rainfall_anomaly_percent = (
    (recent_5yr_mean - longterm_25yr_mean) / longterm_25yr_mean
) * 100

# Interpretation
if rainfall_anomaly_percent < -20:
    status = "Severe Drought"
elif rainfall_anomaly_percent < -10:
    status = "Moderate Drought"
elif rainfall_anomaly_percent > 10:
    status = "Wet Conditions"
else:
    status = "Normal"
```

**Result**: 
- Annual rainfall in mm
- Anomaly percentage (positive = wetter, negative = drier)

---

### 1.6 Elevation & Slope

**Dataset**: `USGS/SRTMGL1_003` (SRTM Global 1 arc-second)
- **Band**: `elevation`
- **Spatial Resolution**: 30 meters (~1 arc-second)
- **Units**: meters above sea level
- **Processing**: Mean over polygon

**Slope Calculation**:
```python
elevation_image = ee.Image('USGS/SRTMGL1_003')
slope = ee.Terrain.slope(elevation_image)  # degrees
```
- **Units**: degrees (°)
- **Range**: 0° (flat) to 90° (vertical)

---

### 1.7 Land Cover & Ecosystem Classification

**Dataset**: `ESA/WorldCover/v200/2021`
- **Resolution**: 10m
- **Processing**: Mode (most frequent class) over polygon

**WorldCover Classes → Ecosystem Mapping**:

| Class | Name | Ecosystem | Sequestration Rate |
|-------|------|-----------|-------------------|
| 10 | Tree cover | **Forest** | Climate-dependent |
| 20 | Shrubland | **Shrubland** | 2.0 tCO2e/ha/yr |
| 30 | Grassland | **Grassland** | 1.5 tCO2e/ha/yr |
| 40 | Cropland | **Cropland** | 0.8 tCO2e/ha/yr |
| 50 | Built-up | **Other** | 0.0 tCO2e/ha/yr |
| 60 | Bare/sparse | **Degraded** | 0.3 tCO2e/ha/yr |
| 70 | Snow/ice | **Other** | 0.0 tCO2e/ha/yr |
| 80 | Water | **Wetland** | 4.0 tCO2e/ha/yr |
| 90 | Herb. wetland | **Wetland** | 4.0 tCO2e/ha/yr |
| 95 | Mangroves | **Mangrove** | 10.0 tCO2e/ha/yr |
| 100 | Moss/lichen | **Other** | 0.0 tCO2e/ha/yr |

---

### 1.8 Latitude Extraction (for Climate Zones)

**Calculation**:
```python
# Get polygon centroid
centroid = geometry.centroid().coordinates()
latitude = centroid[1]  # Index 1 is latitude
```

**Climate Zone Determination**:
- **Tropical**: |latitude| ≤ 23.5°
- **Temperate**: 23.5° < |latitude| ≤ 55°
- **Boreal**: |latitude| > 55°

---

## 2. TIME-SERIES TREND ANALYSIS (2020-2024)

### 2.1 NDVI Trend (5-Year Linear Regression)

**Data Collection**:
```python
years = [2020, 2021, 2022, 2023, 2024]
ndvi_yearly = []

for year in years:
    s2_year = Sentinel2
        .filterDate(f'{year}-01-01', f'{year}-12-31')
        .filterBounds(geometry)
        .filter(cloudCover < 30%)
        .map(mask_s2_clouds)  # SCL masking
    
    ndvi_mean = calculate_ndvi(s2_year).mean()
    ndvi_yearly.append(ndvi_mean)
```

**Linear Regression (Least Squares)**:
```python
n = 5  # number of years
x = [0, 1, 2, 3, 4]  # time indices
y = ndvi_yearly  # NDVI values

# Calculate slope
x_mean = sum(x) / n
y_mean = sum(y) / n

numerator = sum((x[i] - x_mean) * (y[i] - y_mean) for i in range(n))
denominator = sum((x[i] - x_mean) ** 2 for i in range(n))

slope = numerator / denominator if denominator != 0 else 0
```

**Interpretation**:
- **Slope > +0.02**: Improving/Regenerating
- **-0.02 ≤ Slope ≤ +0.02**: Stable
- **Slope < -0.02**: Degrading

---

### 2.2 Fire Burn Scar Detection (MODIS)

**Dataset**: `MODIS/061/MCD64A1` (Burned Area Monthly)
- **Band**: `BurnDate`
- **Time Window**: 2020-2024 (5 years)
- **Resolution**: 500m

**Result**:
- `fire_burn_percent`: Percentage of area burned in 5 years
- `fire_recent_burn`: Boolean (burned in last 2 years)

---

### 2.3 Rainfall Anomaly (25-year vs 5-year)

**Calculation** (already covered in 1.5):
```python
# Long-term baseline (25 years)
longterm_rain = CHIRPS(1999-2024).mean()

# Recent period (5 years)
recent_rain = CHIRPS(2020-2024).mean()

# Anomaly calculation
rainfall_anomaly_percent = ((recent_rain - longterm_rain) / longterm_rain) * 100
```

---

### 2.4 Trend Classification (Composite)

**Logic**:
```python
if ndvi_trend < -0.02 and fire_recent_burn:
    classification = "Degrading (Fire-Impacted)"
elif ndvi_trend < -0.02:
    classification = "Degrading"
elif fire_burn_percent > 30 and fire_recent_burn:
    classification = "Fire-Impacted (Recovering)"
elif rainfall_anomaly_percent < -20:
    classification = "Drought-Stressed"
elif ndvi_trend > 0.02:
    classification = "Improving"
else:
    classification = "Stable"
```

---

## 3. QA/QC METRICS (Data Quality Assessment)

### 3.1 Pixel Count & NDVI Variability

**Pixel Count**:
```python
# Count valid pixels after cloud masking
pixel_count = ndvi_image.reduceRegion(
    reducer=ee.Reducer.count(),
    geometry=geometry,
    scale=10,  # 10m resolution
    bestEffort=True
).get('ndvi')
```

**NDVI Standard Deviation**:
```python
ndvi_stddev = ndvi_image.reduceRegion(
    reducer=ee.Reducer.stdDev(),
    geometry=geometry
).get('ndvi')
```

**Interpretation**:
- **High StdDev (>0.2)**: Heterogeneous landscape (mixed use)
- **Low StdDev (<0.1)**: Homogeneous landscape (monoculture/dense forest)

---

### 3.2 Cloud Coverage (SCL-Based)

**Calculation**:
```python
# Cloud mask (SCL values 8, 9, 10 = clouds/cirrus)
cloud_mask = scl_median.eq(8).Or(scl_median.eq(9)).Or(scl_median.eq(10))

# Calculate percentage
cloud_coverage_percent = (cloudy_pixels / total_pixels) * 100
```

---

### 3.3 GEDI Shot Count

**Dataset**: `LARSE/GEDI/GEDI02_A_002_MONTHLY`
- **Processing**: Count monthly images with data coverage
- **Estimation**: `month_count × 50 shots/month` (conservative)

1. **GEDI Coverage Check**: If no GEDI shots fall within the polygon, we default to Tier 3 (Allometric) and lower the confidence score.

---

### 3.4 Data Confidence Score (0-100)

**Penalty-Based System**:
```python
confidence_score = 100.0  # Start with perfect score

# Penalty 1: Low pixel count (<50) -> -20
# Penalty 2: High cloud coverage (>20%) -> -20
# Penalty 3: No GEDI data -> -10
# Penalty 4: High variability (NDVI StdDev > 0.2) -> -10
# Penalty 5: Low Biomass (<50 t/ha) when forest expected -> -10

confidence_score = max(0, confidence_score)
```

**Interpretation**:
- **80-100**: High confidence - Excellent data quality
- **60-79**: Moderate confidence - Good data quality
- **0-59**: Low confidence - Limited data quality, requires ground truthing

---

## 4. CARBON CALCULATIONS

### 4.1 Biomass Carbon (UPDATED - Now Includes Belowground)

**Previous Formula** (AGB only):
```python
carbon_biomass = biomass_agb × 0.47
```

**NEW Formula** (AGB + BGB):
```python
# Above-ground carbon
carbon_biomass_agb = biomass_agb × 0.47  # tC/ha

# Below-ground carbon (NEW)
carbon_biomass_bgb = biomass_bgb × 0.47  # tC/ha

# Total biomass carbon
carbon_biomass_total = (biomass_agb + biomass_bgb) × 0.47  # tC/ha
```

Where:
- `biomass_agb`: Above-ground biomass in t/ha (from GEDI or allometric, **with bias correction**)
- `biomass_bgb`: Below-ground biomass in t/ha (calculated using IPCC R:S ratios)
- `0.47`: IPCC carbon fraction (47% of dry biomass is carbon)
- **Source**: IPCC 2006 Guidelines Vol 4, Ch 4, Table 4.3

**Example Calculation** (Tropical Forest):
```
Raw GEDI AGB: 300 t/ha
Corrected AGB: 300 × 1.35 = 405 t/ha (+35% correction)
BGB: 405 × 0.24 = 97.2 t/ha (R:S ratio = 0.24)
Total Biomass: 405 + 97.2 = 502.2 t/ha

Carbon AGB: 405 × 0.47 = 190.35 tC/ha
Carbon BGB: 97.2 × 0.47 = 45.68 tC/ha
Total Carbon: 502.2 × 0.47 = 236.03 tC/ha
```

**Result**: 
- `carbon_biomass_agb` in tC/ha (above-ground only)
- `carbon_biomass_bgb` in tC/ha (below-ground only)
- `carbon_biomass_total` in tC (total for entire area)

---

### 4.2 Soil Organic Carbon (Per Hectare)

**Calculation** (from section 1.3):
```python
# For each depth layer (0-30cm typically)
layer_carbon = bulk_density * 0.01 * soc_raw * thickness * 0.1
total_soc_per_ha += layer_carbon
```

**Result**: `soc_total` in tC/ha

---

### 4.3 Climate-Specific Sequestration Rates

**Forest Sequestration** (latitude-dependent):

| Zone | Latitude | Rate (tCO2e/ha/yr) | IPCC Range | Applies To |
|------|----------|-------------------|------------|------------|
| **Boreal** | > 55° | 3.0 | 1.5-4.4 | Canada, Russia |
| **Temperate** | 23.5° - 55° | 11.0 | 5.5-16.5 | USA, EU |
| **Tropical Dry** | ≤ 23.5° | 5.0 | 3.5-6.0 | India, Africa |

---

## 7. LIMITATIONS & AREAS FOR IMPROVEMENT

While our system provides a rigorous preliminary analysis ("Pre-Feasibility Study"), it has limitations compared to on-the-ground verification required for rigorous carbon credit issuance (e.g., Verra VM0047, Gold Standard).

### 7.1 GEDI L4A Biomass Limitations ✅ PARTIALLY ADDRESSED

**What We Fixed**:
- ✅ **Bias Correction Implemented**: We now apply ecosystem-specific correction factors (+10% to +35%) to fix the known -31.65 Mg/ha underestimation bias.
- ✅ **Belowground Biomass Added**: We now include root biomass using IPCC 2019 R:S ratios, adding 20-40% to total carbon stock.

**Remaining Limitations**:
- **Sparse Sampling**: GEDI is not a wall-to-wall imager. It uses laser shots (25m footprint). For small polygons (<20 ha) or irregular shapes, we may rely on interpolated GEDI L4B (1km) or allometric fallbacks, which lowers precision.
- **Temporal Mismatch**: GEDI data availability lags. We use the most recent available year (often 1-2 years behind), which may miss recent deforestation events unless cross-referenced with Sentinel-2/MODIS.
- **Quality Filtering**: We do not yet filter by `l4_quality_flag`. Low-quality GEDI shots may still be included in the median calculation.

### 7.2 Soil Organic Carbon (SOC)
- **Resolution**: OpenLandMap is 250m resolution. This is coarse for small farm-level analysis. It provides a regional average but cannot detect micro-variations due to specific farming practices (e.g., biochar application, no-till) without ground samples.
- **Depth**: We calculate to 30cm or 100cm, but deep soil carbon (>1m) is often significant and missed by standard remote sensing datasets.
- **Uncertainty**: We do not yet provide uncertainty bounds (±95% CI) for SOC estimates.

### 7.3 Allometric Equations (Tier 3 Fallback)
- **Generic Equations**: Our Tier 3 allometric equations are unvalidated generic formulas. They can overestimate by 50% in grasslands and underestimate by 30% in old-growth forests.
- **Missing Validated Models**: We have not yet implemented:
  - **Chave et al. (2014)** for tropical forests (requires wood density and environmental stress)
  - **Jenkins et al. (2003)** for temperate North America (species-specific)

### 7.4 Sequestration Rates
- **Generic Factors**: We use IPCC Tier 1 defaults (regional averages). Real sequestration depends heavily on specific species, soil health, and local management.
- **Young vs. Old Growth**: Our current model differentiates broadly by "Ecosystem" but lacks a "Stand Age" parameter. Young, fast-growing forests sequester carbon much faster than mature, old-growth forests, which are better at *storage*.
- **No Forest Age Integration**: We have not yet integrated Hansen Global Forest Change to determine forest age from disturbance history.

### 7.5 Uncertainty Quantification ❌ NOT YET IMPLEMENTED
- **No Error Bars**: We do not provide ±95% Confidence Intervals (CI) for carbon estimates, which is required by Verra/Gold Standard.
- **No Error Propagation**: We do not propagate uncertainties from GEDI (±30%), SOC (±20%), and sequestration rates (±30%) to final outputs.

### 7.6 Recommendations for Production Use
1.  **Ground Truthing**: Use this tool for *screening*. For final credit issuance, deploy field teams to measure DBH (Diameter at Breast Height) in sample plots to calibrate the satellite estimates.
2.  **Drone LIDAR**: For high-value projects, drone-based LIDAR can provide wall-to-wall canopy models at 5cm resolution, fixing GEDI's coverage gaps.
3.  **Local Allometry**: Replace our "Default Allometric Equations" (Section 1.2, Tier 3) with species-specific equations if the dominant tree species is known.
4.  **Field Validation**: Collect soil samples to validate SOC estimates, especially for projects <100 hectares where 250m resolution is too coarse.

---

## 8. RECENT IMPROVEMENTS (Production Upgrades)

### ✅ Phase 1: GEDI Bias Correction (Completed)
- Implemented ecosystem-specific correction factors based on Taylor & Francis (2023) research
- Tropical forests: +15% to +35% correction depending on biomass density
- Temperate forests: +10% to +20% correction
- Boreal forests: +10% correction

### ✅ Phase 2: Belowground Biomass Integration (Completed)
- Added IPCC 2019 Root-to-Shoot ratios for all ecosystems
- Tropical forests: +24% total biomass
- Temperate forests: +29% total biomass
- Grasslands: +300% total biomass (roots dominate!)
- Separate tracking of AGB, BGB, and Total Biomass

### 🔄 Phase 3: Validated Allometric Equations (In Progress)
- Plan to implement Chave et al. (2014) for tropical forests
- Plan to implement Jenkins et al. (2003) for temperate forests

### 🔄 Phase 4: Uncertainty Quantification (Planned)
- Plan to add ±95% CI for all carbon estimates
- Plan to implement error propagation framework

### 🔄 Phase 5: Forest Age Integration (Planned)
- Plan to integrate Hansen Global Forest Change dataset
- Plan to calculate forest age from disturbance history
- Plan to apply age-dependent sequestration rates

---

## 9. FUTURE ROADMAP

1.  **Complete Remaining Phases**: Finish Phases 3-5 of scientific upgrades
2.  **SoilGrids 2.0 Integration**: Switch to higher-quality SOC data with uncertainty estimates
3.  **User-Upload Field Data**: Allow users to upload CSVs of field plot measurements to auto-correct satellite bias
4.  **AI Pattern Recognition**: Use CNNs on Sentinel-2 imagery to detect specific degradation patterns (logging roads, selective logging)
