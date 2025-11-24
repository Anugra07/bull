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


def analyze_polygon(geojson: Any) -> Dict[str, float]:
    """
    Compute required metrics over the input polygon using Earth Engine.
    Returns a dict with keys: ndvi, evi, biomass, canopy_height, soc, bulk_density, rainfall, elevation, slope
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

    # GEDI canopy height (L2A)
    canopy_h_mean_python = 0.0
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
    
    # Convert to Earth Engine Number with safe default
    canopy_h_mean = ee.Number(max(canopy_h_mean_python, 0.0))

    # Improved Biomass Calculation - Multi-tier approach
    # 1. Try GEDI L4A Above Ground Biomass (AGB) directly
    biomass_mean = ee.Number(0)
    land_cover_class = ee.Number(0)
    
    # Get land cover classification first (needed for fallback)
    land_cover_class_python = 0
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
    
    # Convert to Earth Engine Number
    land_cover_class = ee.Number(land_cover_class_python)
    
    # Build allometric equations first (needed for fallback)
    lc = ee.Number(land_cover_class)
    # Ensure canopy height is at least 0.1m to avoid division issues in allometric equations
    # Use Python max() since canopy_h_mean is created from Python value
    canopy_h_safe_val = max(canopy_h_mean_python, 0.1)
    canopy_h_safe = ee.Number(canopy_h_safe_val)
    
    # Apply ecosystem-specific allometric equations based on land cover
    # WorldCover classes: 10=Trees, 20=Shrubland, 30=Grassland, 40=Cropland, 50=Urban, 60=Bare, 70=Snow/Ice, 80=Water, 90=Herbaceous, 95=Mangroves, 100=Moss
    allometric_biomass = ee.Algorithms.If(
        lc.eq(10).Or(lc.eq(95)),  # Trees or Mangroves
        canopy_h_safe.multiply(15).add(canopy_h_safe.pow(1.5).multiply(2)),  # Forest: ~15*H + 2*H^1.5
        ee.Algorithms.If(
            lc.eq(20),  # Shrubland
            canopy_h_safe.multiply(8).add(canopy_h_safe.pow(1.3).multiply(1.5)),  # Shrub: ~8*H + 1.5*H^1.3
            ee.Algorithms.If(
                lc.eq(30).Or(lc.eq(90)),  # Grassland or Herbaceous
                canopy_h_safe.multiply(3),  # Grass: ~3*H (very low biomass)
                ee.Algorithms.If(
                    lc.eq(40),  # Cropland
                    canopy_h_safe.multiply(5),  # Crops: ~5*H
                    canopy_h_safe.multiply(10).add(canopy_h_safe.pow(1.5).multiply(2))  # Default: improved allometric
                )
            )
        )
    )
    
    # Try GEDI L4A AGB first (most accurate)
    # If available and valid, use it; otherwise use allometric
    # Handle nulls properly by evaluating first, then using in Earth Engine
    gedi_agb_python = None
    try:
        gedi_l4a = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY') \
            .filterBounds(geom) \
            .select(['agbd'])  # Above Ground Biomass Density
        
        # Check if collection has any images first
        gedi_count_info = gedi_l4a.size().getInfo()
        if gedi_count_info > 0:
            agb_image = gedi_l4a.median().rename('agb')
            agb_result_dict = agb_image.reduceRegion(
                ee.Reducer.mean(),
                geom,
                scale=100,
                maxPixels=1e9,
                bestEffort=True
            ).getInfo()
            
            gedi_agb_python = agb_result_dict.get('agb')
    except Exception:
        gedi_agb_python = None
    
    # Use Python-level check, then create Earth Engine expression
    # We'll evaluate biomass to Python and handle max() there to avoid ComputedObject issues
    if gedi_agb_python is not None and isinstance(gedi_agb_python, (int, float)) and gedi_agb_python > 0.1:
        # GEDI AGB is valid and available - use it directly
        # Convert to Earth Engine Number (already in Mg/ha = t/ha)
        biomass_mean = ee.Number(max(gedi_agb_python, 0.0))
    else:
        # GEDI AGB not available or invalid - use allometric
        # allometric_biomass is a ComputedObject - we'll handle max() after evaluation
        biomass_mean = allometric_biomass

    # SoilGrids SOC% and bulk density - try multiple dataset paths
    soc_mean = ee.Number(0)
    bd_mean = ee.Number(0)
    
    # Try OpenLandMap datasets (alternative to SoilGrids)
    try:
        # OpenLandMap Soil Organic Carbon Content
        soc_image = ee.Image('OpenLandMap/SOL/SOL_ORGANIC-CARBON_USDA-6A1C_M/v02').select('b0')
        soc_mean = soc_image.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=250, 
            maxPixels=1e9,
            bestEffort=True
        ).get('b0')
    except Exception:
        try:
            # Alternative: ISRIC SoilGrids 250m
            soc_image = ee.ImageCollection('projects/soilgrids-isric/clay_mean').first()
            soc_mean = soc_image.reduceRegion(
                ee.Reducer.mean(), 
                geom, 
                scale=250, 
                maxPixels=1e9,
                bestEffort=True
            ).get('b0')
        except Exception:
            soc_mean = ee.Number(2.0)  # Default placeholder (2% SOC)
    
    try:
        # OpenLandMap Bulk Density
        bd_image = ee.Image('OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02').select('b0')
        bd_mean = bd_image.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=250, 
            maxPixels=1e9,
            bestEffort=True
        ).get('b0')
    except Exception:
        try:
            # Alternative dataset path
            bd_image = ee.ImageCollection('OpenLandMap/SOL/SOL_BULKDENS-FINEEARTH_USDA-4A1H_M/v02').first()
            bd_mean = bd_image.reduceRegion(
                ee.Reducer.mean(), 
                geom, 
                scale=250, 
                maxPixels=1e9,
                bestEffort=True
            ).get('b0')
        except Exception:
            bd_mean = ee.Number(1.3)  # Default placeholder (1.3 g/cm3)

    # CHIRPS rainfall (mm)
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
    except Exception:
        rainfall_mean = ee.Number(0)

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
    except Exception:
        elevation_mean = ee.Number(0)
        slope_mean = ee.Number(0)

    # Evaluate to client-side numbers
    # Note: canopy_h_mean and land_cover_class are already Python values, convert back to EE for dictionary
    result = ee.Dictionary({
        'ndvi': ndvi_mean,
        'evi': evi_mean,
        'biomass': biomass_mean,
        'canopy_height': canopy_h_mean,  # Already ee.Number from Python value
        'soc': soc_mean,
        'bulk_density': bd_mean,
        'rainfall': rainfall_mean,
        'elevation': elevation_mean,
        'slope': slope_mean,
        'land_cover': land_cover_class,  # Already ee.Number from Python value
    }).getInfo()

    # Coerce to float with defaults
    # Use Python values directly where we have them (canopy_height, land_cover)
    # Ensure biomass is non-negative (handle max operation in Python after evaluation)
    biomass_value = float(result.get('biomass') or 0.0)
    
    return {
        'ndvi': float(result.get('ndvi') or 0.0),
        'evi': float(result.get('evi') or 0.0),
        'biomass': max(biomass_value, 0.0),  # Ensure non-negative
        'canopy_height': float(canopy_h_mean_python),  # Use Python value directly
        'soc': float(result.get('soc') or 0.0),
        'bulk_density': float(result.get('bulk_density') or 0.0),
        'rainfall': float(result.get('rainfall') or 0.0),
        'elevation': float(result.get('elevation') or 0.0),
        'slope': float(result.get('slope') or 0.0),
        'land_cover': float(land_cover_class_python),  # Use Python value directly
    }
