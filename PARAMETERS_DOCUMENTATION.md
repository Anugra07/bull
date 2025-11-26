# Carbon Offset Land Analyzer - Complete Parameters & Calculation Logic

## Overview
This document provides comprehensive documentation of all parameters, datasets, formulas, and calculation logic used in the analysis pipeline from data extraction through final carbon credit computation.

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
- Range: -1 to 1 (typically 0-1 for vegetation)
- Higher values indicate healthier/denser vegetation

**EVI Formula**: `EVI = 2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))`
- NIR = B8 / 10000
- RED = B4 / 10000
- BLUE = B2 / 10000
- Coefficients: G=2.5, C1=6.0, C2=7.5, L=1
- Better for dense vegetation (reduces atmospheric interference)

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

**Tier 2 (Fallback)**: `LARSE/GEDI/GEDI04_A_002`
- Product: GEDI L4A Annual AGBD
- Used if monthly data unavailable

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

**Result**: Biomass in t/ha (tonnes per hectare)

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

**Calculation**:
```python
# Get all burned pixels
fire_collection = MODIS_MCD64A1
    .filterDate('2020-01-01', '2024-12-31')
    .filterBounds(geometry)
    .select('BurnDate')

# Count burned pixels
burned_pixels = fire_collection
    .map(lambda img: img.gt(0))  # BurnDate > 0 means burned
    .sum()  # Total burned pixels

# Calculate percentage
total_pixels = get_total_pixels(geometry, scale=500)
fire_burn_percent = (burned_pixels / total_pixels) * 100

# Recent burn check (last 2 years)
recent_fire = fire_collection
    .filterDate('2023-01-01', '2024-12-31')
    .select('BurnDate')
    .max()

fire_recent_burn = recent_fire > 0
```

**Result**:
- `fire_burn_percent`: Percentage of area burned in 5 years
- `fire_recent_burn`: Boolean (burned in last 2 years)

---

### 2.3 Rainfall Anomaly (25-year vs 5-year)

**Calculation** (already covered in 1.5):
```python
# Long-term baseline (25 years)
longterm_rain = CHIRPS
    .filterDate('1999-01-01', '2024-12-31')
    .select('precipitation')
    .mean()

# Recent period (5 years)
recent_rain = CHIRPS
    .filterDate('2020-01-01', '2024-12-31')
    .select('precipitation')
    .mean()

# Anomaly calculation
rainfall_anomaly_percent = (
    (recent_rain - longterm_rain) / longterm_rain * 100
)
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
    geometry=geometry,
    scale=10
).get('ndvi')
```

**Interpretation**:
- **High StdDev (>0.2)**: Heterogeneous landscape
- **Low StdDev (<0.1)**: Homogeneous landscape

---

### 3.2 Cloud Coverage (SCL-Based)

**Calculation**:
```python
# Get SCL median
scl_collection = Sentinel2_SR_HARMONIZED
    .filterDate('2023-01-01', '2024-12-31')
    .filterBounds(geometry)
    .select('SCL')

scl_median = scl_collection.median()

# Cloud mask (SCL values 8, 9, 10 = clouds/cirrus)
cloud_mask = scl_median.eq(8).Or(scl_median.eq(9)).Or(scl_median.eq(10))

# Calculate percentage
total_pixels = count_pixels(geometry, scale=20)  # SCL is 20m
cloudy_pixels = count_pixels_masked(cloud_mask, geometry, scale=20)

cloud_coverage_percent = (cloudy_pixels / total_pixels) * 100
```

---

### 3.3 GEDI Shot Count

**Dataset**: `LARSE/GEDI/GEDI02_A_002_MONTHLY`
- **Processing**: Count monthly images with data coverage
- **Estimation**: `month_count × 50 shots/month` (conservative)

```python
gedi_monthly = GEDI_L2A_MONTHLY
    .filterBounds(geometry)
    .filterDate('2019-04-01', '2024-12-31')

month_count = gedi_monthly.size()
gedi_shot_count = month_count * 50  # Estimated shots
```

---

### 3.4 Data Confidence Score (0-100)

**Penalty-Based System**:
```python
confidence_score = 100.0  # Start with perfect score

# Penalty 1: Low pixel count
if pixel_count < 50:
    confidence_score -= 20

# Penalty 2: High cloud coverage
if cloud_coverage_percent > 20:
    confidence_score -= 20

# Penalty 3: No GEDI data
if gedi_shot_count == 0:
    confidence_score -= 10

# Penalty 4: High variability
if ndvi_stddev > 0.2:
    confidence_score -= 10

confidence_score = max(0, confidence_score)
```

**Interpretation**:
- **80-100**: High confidence - Excellent data quality
- **60-79**: Moderate confidence - Good data quality
- **0-59**: Low confidence - Limited data quality

---

## 4. CARBON CALCULATIONS

### 4.1 Biomass Carbon

**Formula**: `carbon_biomass = biomass × 0.47`

Where:
- `biomass`: Above-ground biomass in t/ha (from GEDI or allometric)
- `0.47`: IPCC carbon fraction (47% of dry biomass is carbon)
- **Source**: IPCC 2006 Guidelines Vol 4, Ch 4, Table 4.3

**Result**: `carbon_biomass` in tC/ha (tonnes of carbon per hectare)

---

### 4.2 Soil Organic Carbon (Per Hectare)

**Calculation** (from section 1.3):
```python
# For each depth layer
for band, thickness in depth_layers:
    soc_raw = soc_image.select(band)  # g/kg
    bd_raw = bulk_density.select(band)  # needs *0.01 to get g/cm³
    
    # SOC calculation for this layer (tC/ha)
    # Formula: BD (g/cm³) × SOC (g/kg) × thickness (m) × 0.1
    # The 0.1 factor = (1 kg / 1000 g) × (1 t / 1000 kg) × (10000 m²/ha)
    layer_soc = bd_raw * 0.01 * soc_raw * thickness * 0.1
    
    total_soc_per_ha += layer_soc

# Result: tC/ha
```

**Full Explanation of 0.1 Factor**:
- BD in g/cm³ → kg/m³: ×1000
- SOC in g/kg → fraction: ÷1000
- Thickness in meters
- Area conversion m² → ha: ×10000
- Mass kg → tonnes: ÷1000
- Combined: (1000 ÷ 1000 × 10000 ÷ 1000) = 10 ÷ 100 = 0.1

---

### 4.3 Climate-Specific Sequestration Rates

**Forest Sequestration** (latitude-dependent):

```python
def get_forest_sequestration_rate(latitude):
    abs_lat = abs(latitude)
    
    if abs_lat > 55:  # Boreal
        return 3.0  # tCO2e/ha/yr
    elif abs_lat > 23.5:  # Temperate
        return 11.0  # tCO2e/ha/yr
    else:  # Tropical DRY (not rainforest)
        return 5.0  # tCO2e/ha/yr
```

**Rates by Climate Zone**:

| Zone | Latitude | Rate (tCO2e/ha/yr) | IPCC Range | Applies To |
|------|----------|-------------------|------------|------------|
| **Boreal** | \|lat\| > 55° | 3.0 | 1.5-4.4 | Canada, Scandinavia, Russia |
| **Temperate** | 23.5° < \|lat\| ≤ 55° | 11.0 | 5.5-16.5 | USA, Europe, China, Japan |
| **Tropical Dry** | \|lat\| ≤ 23.5° | 5.0 | 3.5-6.0 | India, dry zones |

**Important Note**: 
- IPCC tropical rates of 14-29 tCO2e/ha/yr are for **RAINFORESTS** (Amazon, Congo)
- India and similar regions have **DRY DECIDUOUS forests** with much lower rates (3.5-6.0)
- **DO NOT** use rainforest rates for dry tropical forests

**Other Ecosystems** (fixed rates):

| Ecosystem | Rate (tCO2e/ha/yr) | Source |
|-----------|-------------------|---------|
| Mangrove | 10.0 | IPCC: 8-12 |
| Cropland | 0.8 | Agricultural soils |
| Grassland | 1.5 | Improved management (~1.3 IPCC) |
| Wetland | 4.0 | Peatlands/wetlands (2-5+) |
| Shrubland | 2.0 | Estimated |
| Plantation | 6.0 | Managed plantations |
| Degraded | 0.3 | Minimal recovery |
| Other | 0.0 | No sequestration |

---

### 4.4 Annual CO₂ Sequestration

**Formula**: `annual_co2 = sequestration_rate × area_ha`

```python
area_ha = area_m2 / 10000.0

# Get ecosystem-specific rate
ecosystem_type, params = get_ecosystem_info(land_cover_class, latitude)
sequestration_rate = params['sequestration_rate']

# Calculate annual sequestration
annual_co2 = sequestration_rate * area_ha
```

**Example** (7 hectares of dry tropical forest):
```
Rate: 5.0 tCO2e/ha/yr
Area: 7.0 ha
Annual: 5.0 × 7.0 = 35.0 tCO2e/year ✓ (realistic)
```

**Result**: `annual_co2` in tCO2e/yr

---

### 4.5 20-Year Projection

**Formula**: `co2_20yr = annual_co2 × 20`

**Example**:
```
Annual: 35.0 tCO2e/year
20-year: 35.0 × 20 = 700.0 tCO2e over 20 years
```

---

### 4.6 Risk-Adjusted Carbon (With Time-Series Enhancement)

**Base Risk Factors** (ecosystem-specific):

| Ecosystem | Fire Risk | Drought Risk | Trend Loss |
|-----------|-----------|--------------|------------|
| Forest | 0.08 (8%) | 0.04 (4%) | 0.02 (2%) |
| Mangrove | 0.01 | 0.05 | 0.03 |
| Wetland | 0.01 | 0.08 | 0.04 |
| Grassland | 0.05 | 0.05 | 0.02 |
| Shrubland | 0.06 | 0.05 | 0.02 |
| Cropland | 0.02 | 0.06 | 0.03 |
| Plantation | 0.07 | 0.03 | 0.01 |
| Degraded | 0.03 | 0.07 | 0.05 |

**Enhanced Risk Adjustment** (based on time-series data):

```python
# Start with ecosystem defaults
fire_risk = ecosystem_params['fire_risk']
drought_risk = ecosystem_params['drought_risk']
trend_loss = ecosystem_params['trend_loss']

# Adjust based on actual historical data
if fire_recent_burn:
    fire_risk = min(fire_risk + 0.05, 0.95)  # +5% if recent burn

if fire_burn_percent > 10:
    fire_risk = min(fire_risk + 0.03, 0.95)  # +3% if >10% burned

if rainfall_anomaly_percent < -20:
    drought_risk = min(drought_risk + 0.04, 0.95)  # +4% if severe drought

if ndvi_trend < -0.02:  # Degrading
    trend_loss = min(trend_loss + 0.03, 0.95)  # +3% if degrading

# Calculate adjustment factor
adjustment_factor = max(0.0, 1.0 - fire_risk - drought_risk - trend_loss)

# Apply to 20-year projection
risk_adjusted_co2 = co2_20yr * adjustment_factor
```

**Example** (Forest with recent fire):
```
Base fire_risk: 0.08
Recent burn: +0.05
Adjusted fire_risk: 0.13

Base drought_risk: 0.04
Base trend_loss: 0.02

Adjustment factor: 1.0 - 0.13 - 0.04 - 0.02 = 0.81 (81%)

co2_20yr: 700 tCO2e
Risk-adjusted: 700 × 0.81 = 567 tCO2e
```

---

## 5. BASELINE CARBON STOCK (MRV Compliance)

### 5.1 Baseline Scenarios

The baseline represents **what would happen WITHOUT the project intervention**. This is critical for demonstrating additionality in carbon offset projects.

**Scenario Determination** (based on trend classification):

**Scenario 1: Degrading Trend**
```python
if "Degrading" in trend_classification or ndvi_trend < -0.02:
    baseline_biomass_factor = 0.6  # 60% of current
    baseline_soc_factor = 0.7      # 70% of current
    baseline_seq_rate = 0.0        # No sequestration (continued loss)
    scenario = "Business-as-Usual Degradation"
```

**Scenario 2: Fire-Impacted**
```python
if "Fire" in trend_classification or fire_recent_burn:
    baseline_biomass_factor = 0.4  # 40% of current (severe loss)
    baseline_soc_factor = 0.8      # 80% of current (less soil impact)
    baseline_seq_rate = 0.5        # Minimal recovery (tCO2e/ha/yr)
    scenario = "Post-Fire Degraded State"
```

**Scenario 3: Drought-Stressed**
```python
if "Drought" in trend_classification or rainfall_anomaly_percent < -20:
    baseline_biomass_factor = 0.7  # 70% of current
    baseline_soc_factor = 0.75     # 75% of current
    baseline_seq_rate = 0.8        # Reduced sequestration
    scenario = "Drought-Stressed Degradation"
```

**Scenario 4: Improving (Conservative Baseline)**
```python
if "Improving" in trend_classification or ndvi_trend > 0.02:
    baseline_biomass_factor = 0.85  # 85% (natural improvement assumed)
    baseline_soc_factor = 0.9       # 90%
    baseline_seq_rate = ecosystem_seq_rate * 0.5  # Half the rate
    scenario = "Natural Regeneration (Conservative)"
```

**Scenario 5: Stable (Status Quo)**
```python
else:  # Stable
    baseline_biomass_factor = 0.95  # 95% (slight degradation)
    baseline_soc_factor = 0.95      # 95%
    baseline_seq_rate = ecosystem_seq_rate * 0.3  # 30% of project rate
    scenario = "Status Quo with Slight Degradation"
```

---

### 5.2 Baseline Carbon Stock Calculations

```python
# Current carbon stocks
current_biomass_carbon = biomass * 0.47  # tC/ha
current_soc_total = soc_calculation()    # tC

# Baseline carbon stocks (what it would be without project)
baseline_biomass_carbon = current_biomass_carbon * baseline_biomass_factor
baseline_soc_total = current_soc_total * baseline_soc_factor

# Baseline annual sequestration
area_ha = area_m2 / 10000.0
baseline_annual_co2 = baseline_seq_rate * area_ha

# Baseline 20-year projection
baseline_co2_20yr = baseline_annual_co2 * 20
```

---

### 5.3 Project Carbon Stock (With Intervention)

```python
# Project assumes successful intervention and management
# Uses full ecosystem sequestration rate
project_annual_co2 = ecosystem_seq_rate * area_ha
project_co2_20yr = project_annual_co2 * 20

# Apply risk adjustment (normal project risks)
project_co2_20yr_adjusted = project_co2_20yr * adjustment_factor
```

---

### 5.4 Additionality (Carbon Credits)

**Additionality = Project - Baseline**

```python
# Annual additionality
additionality_annual_co2 = max(0.0, project_annual_co2 - baseline_annual_co2)

# 20-year additionality (total credits)
additionality_20yr = max(0.0, 
    project_co2_20yr_adjusted - baseline_co2_20yr
)
```

**Example** (Fire-impacted forest with restoration project):
```
# Baseline (without project) - degraded state
Baseline annual: 0.5 × 7 ha = 3.5 tCO2e/year
Baseline 20-year: 3.5 × 20 = 70 tCO2e

# Project (with restoration) - managed forest
Project annual: 5.0 × 7 ha = 35 tCO2e/year
Project 20-year: 35 × 20 = 700 tCO2e
Risk-adjusted: 700 × 0.81 = 567 tCO2e

# Additionality (carbon credits)
Annual credits: 35 - 3.5 = 31.5 tCO2e/year
Total credits (20 yr): 567 - 70 = 497 tCO2e ✓
```

**Key Point**: Additionality must be **positive** to qualify for carbon credits. If negative, the project cannot claim credits.

---

## 6. COMPLETE DATA FLOW

```
┌─────────────────────────────────────────────────────────┐
│ 1. POLYGON INPUT (GeoJSON/Feature/Draw)                │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 2. GEOMETRY PROCESSING                                  │
│   • Normalize (handle FeatureCollection/Feature)       │
│   • Validate (Shapely)                                  │
│   • Calculate area (geodesic)                          │
│   • Extract centroid latitude                          │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 3. GOOGLE EARTH ENGINE ANALYSIS                        │
│                                                         │
│   A. Sentinel-2 (10m resolution, SCL masked)          │
│      → NDVI, EVI (seasonal composites)                │
│                                                         │
│   B. GEDI (100m resolution)                           │
│      → Canopy Height (L2A)                            │
│      → Biomass (L4A) or Allometric fallback           │
│                                                         │
│   C. OpenLandMap (250m resolution)                    │
│      → SOC (depth-specific layers)                    │
│      → Bulk Density (depth-specific)                  │
│                                                         │
│   D. CHIRPS (5km resolution)                          │
│      → Annual Rainfall                                │
│      → Rainfall Anomaly (25yr vs 5yr)                 │
│                                                         │
│   E. SRTM (30m resolution)                            │
│      → Elevation                                       │
│      → Slope                                           │
│                                                         │
│   F. ESA WorldCover (10m resolution)                  │
│      → Land Cover Class                               │
│      → Ecosystem Type                                  │
│                                                         │
│   G. Time-Series Analysis (2020-2024)                 │
│      → NDVI Trend (linear regression)                 │
│      → Fire Burn Scars (MODIS)                        │
│      → Trend Classification                           │
│                                                         │
│   H. QA/QC Metrics                                    │
│      → Pixel Count                                     │
│      → NDVI StdDev                                     │
│      → Cloud Coverage (SCL-based)                     │
│      → GEDI Shot Count                                 │
│      → Confidence Score (0-100)                       │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 4. ECOSYSTEM CLASSIFICATION                            │
│   • Land Cover Class → Ecosystem Type                 │
│   • Latitude → Climate Zone (Boreal/Temperate/Tropical)│
│   • Get sequestration rate (climate-specific for forest)│
│   • Get risk factors (fire, drought, trend)           │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 5. CARBON CALCULATIONS                                 │
│                                                         │
│   A. Biomass Carbon                                    │
│      carbon_biomass = biomass × 0.47 (tC/ha)          │
│                                                         │
│   B. Soil Organic Carbon                              │
│      soc_total = Σ(BD × SOC × thickness × 0.1)        │
│                  per layer, then × area               │
│                                                         │
│   C. Annual Sequestration                             │
│      annual_co2 = seq_rate × area_ha                  │
│                                                         │
│   D. 20-Year Projection                               │
│      co2_20yr = annual_co2 × 20                       │
│                                                         │
│   E. Risk Adjustment (time-series enhanced)           │
│      • Adjust risks based on trends                   │
│      • factor = 1 - fire - drought - trend            │
│      • risk_adjusted = co2_20yr × factor              │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 6. BASELINE CALCULATIONS (MRV)                         │
│   • Determine scenario (degrading/fire/drought/etc.)  │
│   • Calculate baseline carbon stocks                  │
│   • Calculate baseline sequestration                  │
│   • Compare: Project vs Baseline                      │
│   • Compute: Additionality (carbon credits)           │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 7. RESULTS OUTPUT                                      │
│                                                         │
│   Metrics:                                             │
│   • NDVI, EVI, biomass, canopy_height                 │
│   • soc, bulk_density, rainfall, elevation, slope     │
│   • land_cover, latitude                              │
│   • ndvi_trend, fire_burn_%, rainfall_anomaly_%       │
│   • trend_classification                              │
│   • pixel_count, cloud_coverage_%, gedi_shot_count    │
│   • data_confidence_score                             │
│                                                         │
│   Carbon:                                              │
│   • carbon_biomass, soc_total                         │
│   • annual_co2, co2_20yr, risk_adjusted_co2           │
│   • ecosystem_type, baseline_condition                │
│                                                         │
│   Baseline (MRV):                                      │
│   • baseline_biomass_carbon, baseline_soc_total       │
│   • baseline_annual_co2, baseline_co2_20yr            │
│   • baseline_scenario (description)                   │
│                                                         │
│   Project:                                             │
│   • project_annual_co2, project_co2_20yr              │
│                                                         │
│   Additionality (Credits):                            │
│   • additionality_annual_co2                          │
│   • additionality_20yr (total carbon credits)         │
└───────────────────────┬─────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│ 8. DATABASE STORAGE                                    │
│   • Insert into project_results table                 │
│   • All metrics + carbon + baseline + additionality   │
└─────────────────────────────────────────────────────────┘
```

---

## 7. CONSTANTS & CONVERSION FACTORS

### 7.1 Molecular Weights
- **CO₂/C Ratio**: 44/12 ≈ 3.67 (not currently used; results in tCO2e)

### 7.2 Area Conversions
- **1 hectare (ha)** = 10,000 m²
- **m² to ha**: `area_ha = area_m2 / 10000`

### 7.3 Density Conversions
- **g/cm³ to kg/m³**: multiply by 1000
- **kg/dm³ to g/cm³**: multiply by 0.01 (OpenLandMap bulk density)

### 7.4 Biomass Carbon Fraction
- **Default**: 0.47 (47%)
- **Source**: IPCC 2006 Guidelines
- **Valid Range**: 0.45-0.50 depending on species

### 7.5 Scaling Factors
- **Sentinel-2 SR**: Bands scaled 0-10000, divide by 10000 for reflectance
- **GEDI L4A**: Biomass in Mg/ha (same as t/ha)
- **OpenLandMap SOC**: g/kg (already a fraction when used with BD)
- **CHIRPS**: mm/day precipitation

---

## 8. API ENDPOINTS

### 8.1 POST /polygons
- **Input**: `{ project_id, geometry }`
- **Processing**: 
  - Normalize geometry (handle FeatureCollection/Feature/Polygon)
  - Validate with Shapely
  - Calculate geodesic area
  - Store in database
- **Output**: `{ id, project_id, area_m2, bbox }`

### 8.2 POST /analysis
- **Input**: `{ polygon_id }` or `{ geometry }`
- **Processing**: All GEE extractions (sections 1-3)
- **Output**: All metrics including time-series and QA/QC

### 8.3 POST /compute
- **Input**: `{ project_id, polygon_id, soil_depth?, risk_params? }`
- **Processing**: 
  - Get analysis results
  - Calculate carbon stocks
  - Determine baseline scenario
  - Calculate additionality
  - Store in database
- **Output**: Carbon calculations + baseline + credits

---

## 9. ERROR HANDLING & FALLBACKS

### 9.1 Data Availability
- **Biomass**: GEDI Monthly → GEDI Annual → Allometric
- **SOC/BD**: OpenLandMap → Defaults (2.0%, 1.3 g/cm³)
- **GEDI Shots**: Monthly count × 50 (estimation)

### 9.2 Geometry Issues
- **Invalid geometry**: Make valid with Shapely
- **FeatureCollection**: Extract first feature
- **Trailing commas in JSON**: Auto-cleaned by FileUpload

### 9.3 Cloud Masking
- **Primary**: SCL band (pixel-level)
- **Fallback**: CLOUDY_PIXEL_PERCENTAGE metadata filter

---

## 10. SCIENTIFIC SOURCES

1. **IPCC 2006 Guidelines for National GHG Inventories** - Volume 4 (AFOLU)
2. **IPCC Special Report on Climate Change and Land (2019)**
3. **Sentinel-2 User Handbook (ESA)**
4. **GEDI L2A/L4A Product Guides (NASA)**
5. **OpenLandMap Documentation (ISRIC)**
6. **CHIRPS Dataset Documentation (UCSB)**
7. **Verra VCS Standard (Carbon Credits)**
8. **Gold Standard for the Global Goals**
9. **Research on dry deciduous forests in India** (NIE, ResearchGate)

---

## REVISION HISTORY

- **2024-11**: Comprehensive documentation created
- **2024-11-25**: 
  - Added Sentinel-2 improvements (SCL masking, 10m resolution, seasonal composites)
  - Updated tropical forest rates (22.0 → 5.0 for dry forests)
  - Added complete time-series analysis documentation
  - Added QA/QC metrics documentation
  - Added baseline carbon stock (MRV) documentation
  - Added detailed data flow diagram

---

## 11. CODE EXECUTION FLOW (Developer Guide)

This section maps the logical steps above to the actual code implementation.

### Step 1: Geometry Processing
- **File**: `backend/app/utils/geo.py`
- **Function**: `normalize_geometry(geojson)`
  - Handles FeatureCollection, Feature, or Geometry input
- **Function**: `clean_and_validate(geom)`
  - Uses Shapely to validate and fix geometry
  - Calculates geodesic area (m²)

### Step 2: Data Extraction (GEE)
- **File**: `backend/app/services/gee.py`
- **Function**: `analyze_polygon(geojson)`
  - **Cloud Masking**: `mask_s2_clouds(image)` (SCL-based)
  - **Sentinel-2**: `s2_collection` setup with seasonal composites
  - **NDVI/EVI**: Calculated at 10m resolution
  - **Time-Series**: Loop through years (2020-2024) for trend analysis
  - **QA/QC**: Pixel count, cloud coverage, GEDI shots
  - **Returns**: Dictionary of raw metrics

### Step 3: Ecosystem Classification
- **File**: `backend/app/services/ecosystem.py`
- **Function**: `get_ecosystem_info(land_cover_class, latitude)`
  - Maps ESA WorldCover class to Ecosystem Type
  - Calls `get_forest_sequestration_rate(latitude)` for climate specifics
  - Returns: `ecosystem_type` and `parameters` (rate, risks)

### Step 4: Carbon Computation
- **File**: `backend/app/services/carbon.py`
- **Function**: `compute_carbon(metrics, ...)`
  - **Biomass Carbon**: `biomass * 0.47`
  - **SOC Total**: `soc_tC_per_ha * area_ha`
  - **Annual CO2**: `sequestration_rate * area_ha`
  - **Risk Adjustment**:
    - Adjusts base risks using `fire_recent_burn`, `rainfall_anomaly`, `ndvi_trend`
    - Calculates `risk_adjusted_co2`
  - **Baseline Calculation**:
    - Determines scenario based on trends
    - Calculates `baseline_annual_co2`
    - Computes `additionality` (Project - Baseline)

### Step 5: API Response
- **File**: `backend/app/routers/compute.py`
- **Endpoint**: `POST /compute`
- **Action**: 
  - Calls `gee.analyze_polygon` (if metrics not cached)
  - Calls `carbon.compute_carbon`
  - Stores results in Supabase
  - Returns complete analysis object
