# Dummy/Placeholder/Default Data Analysis

## Summary
Yes, we are currently using some dummy/placeholder/default values when real data is unavailable. Here's what:

---

## 1. **SOC (Soil Organic Carbon)** - DUMMY DATA ✅
**Location**: `backend/app/services/gee.py:289`

```python
soc_mean = ee.Number(2.0)  # Default placeholder (2% SOC)
```

**When used**: Only if both OpenLandMap SOC datasets fail to load
- Primary: `OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02`
- Fallback: `projects/soilgrids-isric/clay_mean` (incorrect dataset)
- Final fallback: **2.0% SOC** (dummy value)

**Impact**: ⚠️ **Medium** - Affects SOC carbon calculations if soil data unavailable

---

## 2. **Bulk Density** - DUMMY DATA ✅
**Location**: `backend/app/services/gee.py:311`

```python
bd_mean = ee.Number(1.3)  # Default placeholder (1.3 g/cm³)
```

**When used**: Only if both OpenLandMap bulk density datasets fail to load
- Primary: `OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02`
- Fallback: Same dataset accessed as ImageCollection
- Final fallback: **1.3 g/cm³** (dummy value)

**Impact**: ⚠️ **Medium** - Affects SOC carbon calculations if soil data unavailable

---

## 3. **Annual CO2 Sequestration Rate** - PLACEHOLDER ✅
**Location**: `backend/app/services/carbon.py:5`

```python
IPCC_TIER1_DEFAULT_TCO2_HA_YR = 3.0  # conservative default placeholder
```

**When used**: Always (hardcoded default)
- Used for: `annual_co2` and `co2_20yr` calculations
- Comment says: "very coarse placeholder" and "In a real system, index by ecozone/region/land cover"

**Impact**: ⚠️⚠️ **HIGH** - This is a global default, not ecosystem-specific
- Should vary by: ecosystem type, region, climate, forest age, etc.
- Currently applies 3.0 tCO2e/ha/yr to all ecosystems

---

## 4. **Risk Factors** - DEFAULT VALUES (Configurable) ✅
**Location**: `backend/app/services/carbon.py:12-14`

```python
fire_risk: float = 0.05      # 5% default
drought_risk: float = 0.03   # 3% default
trend_loss: float = 0.02     # 2% default
```

**When used**: Default values if user doesn't provide custom values
- Can be overridden via API: `ComputeIn` schema accepts `fire_risk`, `drought_risk`, `trend_loss`
- These are reasonable defaults but should ideally be location/ecosystem-specific

**Impact**: ✅ **Low** - Defaults are reasonable and user-configurable

---

## 5. **Zero Defaults** - NOT DUMMY DATA (Real Failures)
These return `0.0` when data is unavailable, which is appropriate:
- Canopy height: `0.0` if GEDI L2A unavailable
- Biomass: `0.0` if GEDI AGB unavailable AND no canopy height for allometric
- NDVI/EVI: `0.0` if Sentinel-2 unavailable
- Rainfall: `0.0` if CHIRPS unavailable
- Elevation/Slope: `0.0` if SRTM unavailable

**These are correct** - they indicate "no data" rather than fake data.

---

## Recommendations

### Critical Issues:
1. **Annual CO2 Sequestration Rate** (3.0 tCO2e/ha/yr)
   - ❌ Too simplistic - applies same rate to all ecosystems
   - ✅ Should use ecosystem-specific rates based on:
     - Land cover type (forest, grassland, cropland, etc.)
     - Regional/climate factors
     - Forest age/regeneration stage
     - Actual sequestration potential

### Medium Priority:
2. **SOC Default** (2.0%)
   - ✅ Try additional soil datasets before using default
   - ✅ Add more fallback options (SoilGrids, WoSIS, etc.)

3. **Bulk Density Default** (1.3 g/cm³)
   - ✅ Try additional datasets before using default
   - ✅ Could be estimated from soil texture if available

### Low Priority:
4. **Risk Factors**
   - ✅ Consider making them ecosystem/location-specific
   - ✅ Could use historical fire/drought data per region

---

## Current Data Sources (Real, not dummy)

✅ **GEDI L4A AGB** - Real LIDAR measurements (primary biomass source)
✅ **GEDI L2A Canopy Height** - Real LIDAR measurements
✅ **ESA WorldCover** - Real land cover classification
✅ **Sentinel-2** - Real satellite imagery (NDVI/EVI)
✅ **CHIRPS** - Real rainfall data
✅ **SRTM** - Real elevation/slope data
✅ **OpenLandMap SOC/Bulk Density** - Real soil data (when available)

---

*Last Updated: Current implementation analysis*


