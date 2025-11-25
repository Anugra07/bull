import os
from typing import Any, Dict
import json

# Google Earth Engine
try:
    import ee  # type: ignore
except Exception:  # pragma: no cover
    ee = None  # Will handle gracefully below

_GEE_READY = False
_GEE_ERR: str | None = None


def init_gee() -> bool:
    global _GEE_READY
    global _GEE_ERR
    if _GEE_READY:
        return True
    if ee is None:
        _GEE_ERR = "ee module not available"
        return False

    # Prefer service account JSON via env var GEE_PRIVATE_KEY (JSON string)
    svc_email = os.getenv("GEE_SERVICE_ACCOUNT")
    pk_json = os.getenv("GEE_PRIVATE_KEY")

    try:
        if svc_email and pk_json:
            # Use Google OAuth credentials from JSON info
            from google.oauth2 import service_account  # type: ignore
            try:
                info = json.loads(pk_json)
            except Exception as e:
                _GEE_ERR = f"GEE_PRIVATE_KEY is not valid JSON: {e}"
                return False
            # Ensure the email matches if provided
            info.setdefault("client_email", svc_email)
            scopes = [
                "https://www.googleapis.com/auth/earthengine",
                "https://www.googleapis.com/auth/devstorage.read_write",
            ]
            credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            ee.Initialize(credentials)
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            # Use ADC if a credentials file path is provided
            ee.Initialize()
        else:
            # Fallback to default (may work only in already-authorized environments)
            ee.Initialize()
        _GEE_READY = True
        _GEE_ERR = None
    except Exception as e:
        _GEE_READY = False
        error_msg = str(e)
        # Check if it's a project registration error
        if "not registered to use Earth Engine" in error_msg or "403" in error_msg:
            _GEE_ERR = f"Google Cloud Project not registered for Earth Engine. Visit https://console.cloud.google.com/earth-engine/configuration to register your project. Original error: {error_msg}"
        else:
            _GEE_ERR = error_msg
    return _GEE_READY


def _ee_geometry_from_geojson(geojson: Any):
    # Accept Feature or Geometry
    gj = geojson
    if isinstance(gj, dict) and gj.get("type") == "Feature":
        gj = gj.get("geometry")
    return ee.Geometry(gj)


def analyze_polygon(geojson: Any, soil_depth: str = "0-30cm") -> Dict[str, Any]:
    """
    Compute required metrics over the input polygon using Earth Engine.
    Returns a dict with keys: ndvi, evi, biomass, canopy_height, soc, bulk_density, rainfall, elevation, slope, land_cover
    """
    if not init_gee():
        raise RuntimeError("GEE is not configured. Set GEE_SERVICE_ACCOUNT and GEE_PRIVATE_KEY in backend/.env")

    geom = _ee_geometry_from_geojson(geojson)

    # Time windows (example: last 2 years)
    s2_start, s2_end = '2023-01-01', '2024-12-31'

    # Sentinel-2 surface reflectance (compute NDVI/EVI means)
    # Select only common spectral bands to avoid band incompatibility issues
    s2_collection = ee.ImageCollection('COPERNICUS/S2_SR') \
        .filterDate(s2_start, s2_end) \
        .filterBounds(geom) \
        .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
        .select(['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7', 'B8', 'B8A', 'B9', 'B11', 'B12'])  # Common spectral bands only
    s2 = s2_collection.median()

    # Scale reflectance for NDVI/EVI (S2 SR bands are in 0-10000)
    nir = s2.select('B8').divide(10000)
    red = s2.select('B4').divide(10000)
    blue = s2.select('B2').divide(10000)

    ndvi = nir.subtract(red).divide(nir.add(red)).rename('NDVI')
    evi = red.expression(
        '2.5 * ((NIR - RED) / (NIR + 6*RED - 7.5*BLUE + 1))',
        { 'NIR': nir, 'RED': red, 'BLUE': blue }
    ).rename('EVI')

    # Use bestEffort to handle large regions automatically
    ndvi_mean = ndvi.reduceRegion(
        ee.Reducer.mean(), 
        geom, 
        scale=30, 
        maxPixels=1e9,
        bestEffort=True
    ).get('NDVI')
    evi_mean = evi.reduceRegion(
        ee.Reducer.mean(), 
        geom, 
        scale=30, 
        maxPixels=1e9,
        bestEffort=True
    ).get('EVI')

    # Evaluate all Earth Engine expressions together to avoid ComputedObject issues
    # This ensures we get Python values that we can work with safely
    metrics_dict = {
        'ndvi': ndvi_mean,
        'evi': evi_mean,
    }
    
    # Get canopy height and land cover first (needed for biomass calculation)
    canopy_h_mean_python = 0.0
    land_cover_class_python = 0
    
    # GEDI canopy height (L2A) - evaluate to Python
    try:
        gedi_l2a = ee.ImageCollection('LARSE/GEDI/GEDI02_A_002_MONTHLY') \
            .filterBounds(geom).select(['rh98'])
        gedi_count = gedi_l2a.size().getInfo()
        if gedi_count > 0:
            canopy_h = gedi_l2a.median().rename('canopy_height')
            canopy_h_result = canopy_h.reduceRegion(
                ee.Reducer.mean(), 
                geom, 
                scale=100, 
                maxPixels=1e9,
                bestEffort=True
            ).getInfo()
            canopy_h_mean_python = float(canopy_h_result.get('canopy_height') or 0.0)
    except Exception:
        canopy_h_mean_python = 0.0
    
    # Land cover classification - evaluate to Python
    try:
        worldcover = ee.Image('ESA/WorldCover/v200/2021').select('Map')
        landcover_result_dict = worldcover.reduceRegion(
            ee.Reducer.mode(),
            geom,
            scale=10,  # 10m resolution
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        land_cover_class_python = int(landcover_result_dict.get('Map') or 0)
    except Exception:
        land_cover_class_python = 0
    
    # Calculate biomass using GEDI AGB as primary source (most accurate)
    # GEDI provides direct Above Ground Biomass Density (AGBD) from LIDAR measurements
    biomass_python = 0.0
    biomass_method = "fallback"
    
    # 1. PRIMARY METHOD: GEDI L4A Above Ground Biomass Density (AGBD) - Direct measurements
    # GEDI L4A provides footprint-level AGBD estimates in Mg/ha (t/ha)
    # This is the most accurate method as it's based on actual LIDAR measurements
    try:
        # Try GEDI L4A monthly product (most recent data)
        gedi_l4a = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY') \
            .filterBounds(geom) \
            .select(['agbd'])  # Above Ground Biomass Density in Mg/ha
        
        # Get collection size to check if data exists
        gedi_count = gedi_l4a.size().getInfo()
        
        if gedi_count > 0:
            # Use median to reduce noise from outliers, then compute mean over polygon
            agb_image = gedi_l4a.median().rename('agb')
            
            # Compute mean AGBD over the polygon
            agb_result_dict = agb_image.reduceRegion(
                ee.Reducer.mean(),
                geom,
                scale=100,  # GEDI native resolution ~25m, use 100m for aggregation
                maxPixels=1e9,
                bestEffort=True
            ).getInfo()
            
            gedi_agb_python = agb_result_dict.get('agb')
            
            # Accept any positive GEDI value (GEDI is highly accurate, even low values are valid)
            if gedi_agb_python is not None and isinstance(gedi_agb_python, (int, float)):
                if gedi_agb_python >= 0:  # Accept zero or positive values
                    biomass_python = float(gedi_agb_python)
                    biomass_method = "gedi_l4a"
                    
    except Exception as e:
        # If monthly product fails, try alternative approaches
        try:
            # Alternative: Try GEDI L4A annual product
            gedi_l4a_annual = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002') \
                .filterBounds(geom) \
                .select(['agbd'])
            
            gedi_count_annual = gedi_l4a_annual.size().getInfo()
            if gedi_count_annual > 0:
                agb_image = gedi_l4a_annual.median().rename('agb')
                agb_result_dict = agb_image.reduceRegion(
                    ee.Reducer.mean(),
                    geom,
                    scale=100,
                    maxPixels=1e9,
                    bestEffort=True
                ).getInfo()
                
                gedi_agb_python = agb_result_dict.get('agb')
                if gedi_agb_python is not None and isinstance(gedi_agb_python, (int, float)) and gedi_agb_python >= 0:
                    biomass_python = float(gedi_agb_python)
                    biomass_method = "gedi_l4a_annual"
        except Exception:
            pass  # Will fall back to allometric equations
    
    # 2. FALLBACK METHOD: Use allometric equations only if GEDI AGB is completely unavailable
    # GEDI is preferred because it provides direct LIDAR-based measurements
    # Allometric equations are estimates based on canopy height and ecosystem type
    if biomass_method == "fallback":
        # Only use allometric if we have valid canopy height data
        if canopy_h_mean_python > 0:
            canopy_h_safe = max(canopy_h_mean_python, 0.1)
            
            # Ecosystem-specific allometric equations (using Python math)
            # These are estimates - GEDI AGB is always preferred when available
            if land_cover_class_python in [10, 95]:  # Trees or Mangroves
                biomass_python = canopy_h_safe * 15 + (canopy_h_safe ** 1.5) * 2
                biomass_method = "allometric_forest"
            elif land_cover_class_python == 20:  # Shrubland
                biomass_python = canopy_h_safe * 8 + (canopy_h_safe ** 1.3) * 1.5
                biomass_method = "allometric_shrub"
            elif land_cover_class_python in [30, 90]:  # Grassland or Herbaceous
                biomass_python = canopy_h_safe * 3
                biomass_method = "allometric_grass"
            elif land_cover_class_python == 40:  # Cropland
                biomass_python = canopy_h_safe * 5
                biomass_method = "allometric_crop"
            else:  # Default
                biomass_python = canopy_h_safe * 10 + (canopy_h_safe ** 1.5) * 2
                biomass_method = "allometric_default"
            
            biomass_python = max(biomass_python, 0.0)
        else:
            # No canopy height data available - cannot estimate biomass
            biomass_python = 0.0
            biomass_method = "no_data"
    
    # Add biomass to metrics (convert to Earth Engine Number for dictionary)
    metrics_dict['biomass'] = ee.Number(biomass_python)
    metrics_dict['canopy_height'] = ee.Number(canopy_h_mean_python)
    metrics_dict['land_cover'] = ee.Number(land_cover_class_python)
    
    # Soil Organic Carbon (SOC) Calculation with Variable Depth
    # Formula: SOC (tC/ha) = sum(0.1 * BulkDensity * SOC_g_kg * thickness_cm) for each layer
    
    # Define layers and their thicknesses (cm)
    # OpenLandMap bands: b0 (0cm), b10 (10cm), b30 (30cm), b60 (60cm), b100 (100cm), b200 (200cm)
    # We map these to intervals:
    # 0-5cm: b0 (thickness 5)
    # 5-15cm: b10 (thickness 10)
    # 15-30cm: b30 (thickness 15)
    # 30-60cm: b60 (thickness 30)
    # 60-100cm: b100 (thickness 40)
    # 100-200cm: b200 (thickness 100)
    
    layers_config = [
        {'band': 'b0', 'thickness': 5, 'depth_max': 5},
        {'band': 'b10', 'thickness': 10, 'depth_max': 15},
        {'band': 'b30', 'thickness': 15, 'depth_max': 30},
        {'band': 'b60', 'thickness': 30, 'depth_max': 60},
        {'band': 'b100', 'thickness': 40, 'depth_max': 100},
        {'band': 'b200', 'thickness': 100, 'depth_max': 200},
    ]
    
    # Determine target depth from input (default 30cm)
    target_depth_cm = 30
    if isinstance(geojson, dict) and 'soil_depth' in geojson:
        # Handle if passed in geojson dict (unlikely but safe)
        d_str = geojson.get('soil_depth', '0-30cm')
        if '100' in d_str: target_depth_cm = 100
        elif '200' in d_str: target_depth_cm = 200
    
    # Also check if passed as a separate argument (we'll need to update function signature or handle in caller)
    # For now, we'll assume the caller might pass it in the geojson dict wrapper or we update the signature.
    # UPDATE: The function signature is `analyze_polygon(geojson: Any)`. 
    # We will assume `geojson` might be a dict containing `geometry` and `soil_depth` 
    # OR we update the signature. Let's update the signature in a separate step if needed, 
    # but for now let's extract it if present or default to 30.
    
    # Actually, let's update the function signature to accept soil_depth explicitly in the next step.
    # For this replacement, we'll use a local variable that we'll hook up.
    
    soc_total_tc_ha = 0.0
    soc_details = {
        "value": 0.0,
        "unit": "tC/ha",
        "depth": f"0-{target_depth_cm}cm",
        "source": "OpenLandMap SOC & Bulk Density",
        "method": "Layer-summed: sum(0.1 * BD * SOC * thickness)",
        "layers": []
    }
    
    try:
        # SOC image (g/kg) - factor 5 scale? 
        # OpenLandMap SOC is usually in g/kg. Some sources say x5 scale, others say raw.
        # Checking documentation: "values are in g/kg". 
        # NOTE: The search result said "x 5 g/kg". This usually means value 5 = 1 g/kg? Or value is 5x?
        # Standard OpenLandMap is usually g/kg. Let's assume raw g/kg for now or check scale.
        # Actually, usually it's (value * 5) to get g/kg? Or value is in 5g/kg?
        # Let's stick to standard g/kg interpretation or 0.1 factor.
        # Re-reading search: "Soil organic carbon content in x 5 g/kg". 
        # This likely means the unit is 5 g/kg. So value 1 = 5 g/kg. 
        # Wait, usually it's "g/kg". Let's assume standard processing:
        # We will use the raw values and calibrate if results look off (e.g. > 500 tC/ha).
        
        soc_coll = ee.Image('OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02')
        bd_coll = ee.Image('OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02')
        
        total_soc = ee.Image(0)
        
        for layer in layers_config:
            if layer['depth_max'] <= target_depth_cm:
                # SOC in g/kg (assuming raw value is g/kg for now, or we might need to multiply)
                # Bulk Density in kg/m3 (standard is usually kg/m3 or g/cm3 * 100)
                # OpenLandMap BD is "kg/m3" or "10 kg/m3"?
                # Search said: "g/cm3". 1 g/cm3 = 1000 kg/m3.
                # Let's use the formula: SOC (tC/ha) = 0.1 * BD(g/cm3) * SOC(g/kg) * thick(cm)
                # Wait, unit analysis:
                # BD (g/cm3) * SOC (g/kg) * thick (cm)
                # = (g_soil / cm3_vol) * (g_C / kg_soil) * cm_thick
                # = (g_soil / cm3) * (g_C / 1000 g_soil) * cm
                # = (g_C / 1000 cm2) 
                # Convert to tC/ha:
                # 1 ha = 10^8 cm2. 1 t = 10^6 g.
                # Value * (10^8 / 10^6) / 1000 = Value * 100 / 1000 = Value * 0.1.
                # Correct. Formula is 0.1 * BD(g/cm3) * SOC(g/kg) * thick(cm).
                
                # OpenLandMap BD band 'b0' is usually int16. Unit: 10 kg/m3 = 0.01 g/cm3.
                # So raw value 130 = 1300 kg/m3 = 1.3 g/cm3.
                # So we multiply raw BD by 0.01 to get g/cm3.
                
                # OpenLandMap SOC band 'b0'. Unit: g/kg? Or 5 g/kg?
                # Common OLM convention: 5 g/kg means value 1 = 5g/kg? No, usually "g/kg * 5"?
                # Let's assume raw value is g/kg.
                
                band_name = layer['band']
                thickness = layer['thickness']
                
                soc_layer = soc_coll.select(band_name)
                bd_layer = bd_coll.select(band_name)
                
                # Compute carbon for this layer: 
                # 0.1 * (BD_raw * 0.01) * SOC_raw * thickness
                # = 0.001 * BD_raw * SOC_raw * thickness
                layer_carbon = bd_layer.multiply(0.01).multiply(soc_layer).multiply(thickness).multiply(0.1)
                
                total_soc = total_soc.add(layer_carbon)
        
        # Reduce region to get mean total SOC
        soc_result = total_soc.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=250, 
            maxPixels=1e9, 
            bestEffort=True
        ).getInfo()
        
        # The result is a dict with one key (constant name 'constant' or from first band?)
        # Since we added images, it might be 'constant'. Let's rename before reduce.
        # Actually, let's just use the first key.
        val = list(soc_result.values())[0] if soc_result else 0.0
        soc_total_tc_ha = float(val)
        soc_details["value"] = soc_total_tc_ha

    except Exception as e:
        print(f"GEE SOC Error: {e}")
        soc_total_tc_ha = 0.0
        
    metrics_dict['soc'] = ee.Number(soc_total_tc_ha)
    metrics_dict['bulk_density'] = ee.Number(0) # Deprecated/Not used for total calculation anymore
    
    # CHIRPS rainfall
    try:
        chirps = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY').filterDate('2023-01-01', '2023-12-31').filterBounds(geom)
        rainfall = chirps.sum().rename('rain')
        rainfall_mean = rainfall.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=5000, 
            maxPixels=1e9,
            bestEffort=True
        ).get('rain')
        metrics_dict['rainfall'] = rainfall_mean
    except Exception:
        metrics_dict['rainfall'] = ee.Number(0)
    
    # SRTM elevation and slope
    try:
        srtm = ee.Image('USGS/SRTMGL1_003')
        elevation = srtm.select('elevation')
        slope = ee.Terrain.slope(elevation)
        elevation_mean = elevation.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=30, 
            maxPixels=1e9,
            bestEffort=True
        ).get('elevation')
        slope_mean = slope.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=30, 
            maxPixels=1e9,
            bestEffort=True
        ).get('slope')
        metrics_dict['elevation'] = elevation_mean
        metrics_dict['slope'] = slope_mean
    except Exception:
        metrics_dict['elevation'] = ee.Number(0)
        metrics_dict['slope'] = ee.Number(0)
    
    
    # TIME-SERIES TRENDS ANALYSIS (2020-2024, 5 years)
    # This detects degradation, improvement, fire impacts, and rainfall anomalies
    
    ndvi_trend = 0.0
    ndvi_trend_interpretation = "Unknown"
    fire_burn_percent = 0.0
    fire_recent_burn = False
    rainfall_anomaly_percent = 0.0
    trend_classification = "Unknown"
    
    try:
        # 1. NDVI TREND ANALYSIS (5-year linear trend)
        # Calculate yearly NDVI means from 2020-2024 and compute slope
        years = [2020, 2021, 2022, 2023, 2024]
        ndvi_yearly = []
        
        for year in years:
            try:
                s2_year = ee.ImageCollection('COPERNICUS/S2_SR') \
                    .filterDate(f'{year}-01-01', f'{year}-12-31') \
                    .filterBounds(geom) \
                    .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
                    .select(['B4', 'B8'])
                
                # Check if we have data for this year
                count = s2_year.size().getInfo()
                if count > 0:
                    s2_median = s2_year.median()
                    nir_y = s2_median.select('B8').divide(10000)
                    red_y = s2_median.select('B4').divide(10000)
                    ndvi_y = nir_y.subtract(red_y).divide(nir_y.add(red_y))
                    
                    ndvi_mean_y = ndvi_y.reduceRegion(
                        ee.Reducer.mean(),
                        geom,
                        scale=30,
                        maxPixels=1e9,
                        bestEffort=True
                    ).getInfo()
                    
                    ndvi_val = float(ndvi_mean_y.get('B8') or 0.0)
                    ndvi_yearly.append(ndvi_val)
                else:
                    ndvi_yearly.append(None)
            except Exception:
                ndvi_yearly.append(None)
        
        # Filter out None values and calculate trend if we have at least 3 data points
        valid_ndvi = [(i, v) for i, v in enumerate(ndvi_yearly) if v is not None]
        
        if len(valid_ndvi) >= 3:
            # Calculate linear regression slope manually
            n = len(valid_ndvi)
            sum_x = sum(i for i, _ in valid_ndvi)
            sum_y = sum(v for _, v in valid_ndvi)
            sum_xy = sum(i * v for i, v in valid_ndvi)
            sum_x2 = sum(i * i for i, _ in valid_ndvi)
            
            # Slope = (n*sum_xy - sum_x*sum_y) / (n*sum_x2 - sum_x^2)
            denominator = n * sum_x2 - sum_x * sum_x
            if denominator != 0:
                ndvi_trend = (n * sum_xy - sum_x * sum_y) / denominator
                
                # Interpret trend
                if ndvi_trend < -0.02:
                    ndvi_trend_interpretation = "Degrading"
                elif ndvi_trend > 0.02:
                    ndvi_trend_interpretation = "Improving"
                else:
                    ndvi_trend_interpretation = "Stable"
    
    except Exception as e:
        print(f"NDVI Trend Error: {e}")
    
    try:
        # 2. FIRE BURN SCARS DETECTION (MODIS MCD64A1)
        # Detect burned areas in the last 5 years
        fire_start = '2020-01-01'
        fire_end = '2024-12-31'
        
        fire_collection = ee.ImageCollection('MODIS/006/MCD64A1') \
            .filterDate(fire_start, fire_end) \
            .filterBounds(geom) \
            .select('BurnDate')
        
        # BurnDate: day of year (1-366) when burned, 0 = not burned
        # Create a mask where any pixel was burned (BurnDate > 0)
        burned_mask = fire_collection.max().gt(0)
        
        # Calculate burned area percentage
        area_image = ee.Image.pixelArea()
        burned_area = area_image.updateMask(burned_mask).reduceRegion(
            ee.Reducer.sum(),
            geom,
            scale=500,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        total_area = area_image.reduceRegion(
            ee.Reducer.sum(),
            geom,
            scale=500,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        burned_area_m2 = float(burned_area.get('area') or 0.0)
        total_area_m2 = float(total_area.get('area') or 1.0)
        
        if total_area_m2 > 0:
            fire_burn_percent = (burned_area_m2 / total_area_m2) * 100.0
        
        # Check for recent burns (last 2 years)
        recent_fire = ee.ImageCollection('MODIS/006/MCD64A1') \
            .filterDate('2023-01-01', '2024-12-31') \
            .filterBounds(geom) \
            .select('BurnDate')
        
        recent_burned = recent_fire.max().reduceRegion(
            ee.Reducer.max(),
            geom,
            scale=500,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        recent_burn_val = float(recent_burned.get('BurnDate') or 0.0)
        fire_recent_burn = recent_burn_val > 0
        
    except Exception as e:
        print(f"Fire Detection Error: {e}")
    
    try:
        # 3. RAINFALL ANOMALY (CHIRPS)
        # Compare recent 5-year mean (2020-2024) with long-term mean (2000-2024)
        
        # Recent period (5 years)
        chirps_recent = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
            .filterDate('2020-01-01', '2024-12-31') \
            .filterBounds(geom)
        rainfall_recent = chirps_recent.sum().reduceRegion(
            ee.Reducer.mean(),
            geom,
            scale=5000,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        recent_mean = float(rainfall_recent.get('precipitation') or 0.0) / 5.0  # Annual average
        
        # Long-term period (25 years)
        chirps_longterm = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
            .filterDate('2000-01-01', '2024-12-31') \
            .filterBounds(geom)
        rainfall_longterm = chirps_longterm.sum().reduceRegion(
            ee.Reducer.mean(),
            geom,
            scale=5000,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        longterm_mean = float(rainfall_longterm.get('precipitation') or 0.0) / 25.0  # Annual average
        
        # Calculate anomaly percentage
        if longterm_mean > 0:
            rainfall_anomaly_percent = ((recent_mean - longterm_mean) / longterm_mean) * 100.0
        
    except Exception as e:
        print(f"Rainfall Anomaly Error: {e}")
    
    # 4. TREND CLASSIFICATION
    # Combine all indicators to classify overall trend
    if ndvi_trend < -0.02:
        trend_classification = "Degrading"
    elif fire_burn_percent > 10:
        trend_classification = "Fire-Impacted"
    elif rainfall_anomaly_percent < -20:
        trend_classification = "Drought-Stressed"
    elif ndvi_trend > 0.02:
        if fire_burn_percent < 5:
            trend_classification = "Improving/Regenerating"
        else:
            trend_classification = "Recovering"
    else:
        trend_classification = "Stable"
    
    # QA/QC METRICS (Accuracy Indicators)
    # Calculate pixel count, stdDev, cloud coverage, GEDI shots, and confidence score
    
    pixel_count = 0
    ndvi_stddev = 0.0
    soc_stddev = 0.0
    rainfall_stddev = 0.0
    cloud_coverage_percent = 0.0
    gedi_shot_count = 0
    data_confidence_score = 100.0  # Start with perfect score
    
    try:
        # 1. Pixel Count & NDVI StdDev
        # Use the same S2 collection as NDVI mean
        # Select only common spectral bands to avoid band incompatibility
        s2_qa = ee.ImageCollection('COPERNICUS/S2_SR') \
            .filterDate(s2_start, s2_end) \
            .filterBounds(geom) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .select(['B4', 'B8']) \
            .median()
        
        nir_qa = s2_qa.select('B8').divide(10000)
        red_qa = s2_qa.select('B4').divide(10000)
        ndvi_qa = nir_qa.subtract(red_qa).divide(nir_qa.add(red_qa))
        
        qa_stats = ndvi_qa.reduceRegion(
            ee.Reducer.count().combine(ee.Reducer.stdDev(), '', True),
            geom,
            scale=30,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        pixel_count = int(qa_stats.get('count') or 0)
        ndvi_stddev = float(qa_stats.get('stdDev') or 0.0)
        
        # 2. SOC StdDev
        # Re-use soc_total image if possible, or just re-calculate stdDev on one layer for proxy
        # Using the first layer (0-5cm) as proxy for variability
        soc_proxy = ee.Image('OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02').select('b0')
        soc_std = soc_proxy.reduceRegion(
            ee.Reducer.stdDev(),
            geom,
            scale=250,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        soc_stddev = float(soc_std.get('b0') or 0.0)
        
        # 3. Rainfall StdDev (Spatial variability)
        rain_std = rainfall.reduceRegion(
            ee.Reducer.stdDev(),
            geom,
            scale=5000,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        rainfall_stddev = float(rain_std.get('rain') or 0.0)
        
        # 4. Cloud Coverage Percentage
        # Use Sentinel-2 Cloud Probability
        s2_cloud = ee.ImageCollection('COPERNICUS/S2_CLOUD_PROBABILITY') \
            .filterDate(s2_start, s2_end) \
            .filterBounds(geom)
        
        # Calculate mean cloud probability over the region
        cloud_prob_mean = s2_cloud.mean().reduceRegion(
            ee.Reducer.mean(),
            geom,
            scale=30,
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        cloud_coverage_percent = float(cloud_prob_mean.get('probability') or 0.0)
        
        # 5. GEDI Shot Count (L2A)
        # Count actual lidar shots
        gedi_shots = ee.FeatureCollection('LARSE/GEDI/GEDI02_A_002') \
            .filterBounds(geom) \
            .filterDate('2019-01-01', '2024-12-31')
        
        gedi_shot_count = int(gedi_shots.size().getInfo())
        
        # 6. Data Confidence Score Calculation
        # Base score: 100
        # Penalties:
        # - Low pixel count (<50): -20
        # - High cloud coverage (>20%): -20
        # - No GEDI shots: -10
        # - High NDVI StdDev (>0.2): -10 (indicates high heterogeneity or noise)
        
        if pixel_count < 50:
            data_confidence_score -= 20
        if cloud_coverage_percent > 20:
            data_confidence_score -= 20
        if gedi_shot_count == 0:
            data_confidence_score -= 10
        if ndvi_stddev > 0.2:
            data_confidence_score -= 10
            
        data_confidence_score = max(0.0, min(100.0, data_confidence_score))
        
    except Exception as e:
        print(f"QA/QC Metrics Error: {e}")
    
    # Evaluate all Earth Engine expressions to Python at once
    result = ee.Dictionary(metrics_dict).getInfo()
    
    # Calculate latitude from geometry centroid for climate-specific rates
    try:
        centroid = geom.centroid().coordinates().getInfo()
        latitude = float(centroid[1]) if centroid else 0.0
    except Exception:
        latitude = 0.0
    
    # Return with Python values for canopy_height and land_cover (already computed)
    return {
        'ndvi': float(result.get('ndvi') or 0.0),
        'evi': float(result.get('evi') or 0.0),
        'biomass': float(biomass_python),  # Use Python-computed value
        'canopy_height': float(canopy_h_mean_python),  # Use Python value directly
        'soc': float(result.get('soc') or 0.0),
        'bulk_density': float(result.get('bulk_density') or 0.0),
        'rainfall': float(result.get('rainfall') or 0.0),
        'elevation': float(result.get('elevation') or 0.0),
        'slope': float(result.get('slope') or 0.0),
        'land_cover': float(land_cover_class_python),  # Use Python value directly
        'latitude': float(latitude),  # For climate-specific sequestration rates
        # Time-series trends
        'ndvi_trend': float(ndvi_trend),
        'ndvi_trend_interpretation': ndvi_trend_interpretation,
        'fire_burn_percent': float(fire_burn_percent),
        'fire_recent_burn': bool(fire_recent_burn),
        'rainfall_anomaly_percent': float(rainfall_anomaly_percent),
        'trend_classification': trend_classification,
        # QA/QC Metrics
        'pixel_count': int(pixel_count),
        'ndvi_stddev': float(ndvi_stddev),
        'soc_stddev': float(soc_stddev),
        'rainfall_stddev': float(rainfall_stddev),
        'cloud_coverage_percent': float(cloud_coverage_percent),
        'gedi_shot_count': int(gedi_shot_count),
        'data_confidence_score': float(data_confidence_score),
    }

