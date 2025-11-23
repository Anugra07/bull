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

    # GEDI canopy height/biomass (datasets availability varies)
    # Using GEDI L2A canopy height as example (meters). Biomass often derived from models; placeholder here.
    try:
        gedi = ee.ImageCollection('LARSE/GEDI/GEDI02_A_002_MONTHLY') \
            .filterBounds(geom).select(['rh98'])
        canopy_h = gedi.median().rename('canopy_height')
        canopy_h_mean = canopy_h.reduceRegion(
            ee.Reducer.mean(), 
            geom, 
            scale=100, 
            maxPixels=1e9,
            bestEffort=True
        ).get('canopy_height')
    except Exception:
        canopy_h_mean = ee.Number(0)

    # Placeholder biomass from canopy height with simple proxy (domain users may replace with calibrated model)
    biomass_mean = ee.Number(canopy_h_mean).multiply(10)  # very rough placeholder

    # ESA WorldCover distribution is complex; for MVP return 0 (not requested as scalar)

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
    result = ee.Dictionary({
        'ndvi': ndvi_mean,
        'evi': evi_mean,
        'biomass': biomass_mean,
        'canopy_height': canopy_h_mean,
        'soc': soc_mean,
        'bulk_density': bd_mean,
        'rainfall': rainfall_mean,
        'elevation': elevation_mean,
        'slope': slope_mean,
    }).getInfo()

    # Coerce to float with defaults
    return {
        'ndvi': float(result.get('ndvi') or 0.0),
        'evi': float(result.get('evi') or 0.0),
        'biomass': float(result.get('biomass') or 0.0),
        'canopy_height': float(result.get('canopy_height') or 0.0),
        'soc': float(result.get('soc') or 0.0),
        'bulk_density': float(result.get('bulk_density') or 0.0),
        'rainfall': float(result.get('rainfall') or 0.0),
        'elevation': float(result.get('elevation') or 0.0),
        'slope': float(result.get('slope') or 0.0),
    }
