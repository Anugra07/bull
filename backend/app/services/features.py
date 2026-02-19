import ee
from datetime import datetime, timedelta
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

# Ensure GEE is initialized (usually done in app startup, but safe to check)
# from app.services.gee import init_gee

def extract_features_for_plot(latitude: float, longitude: float, date_str: str) -> Dict[str, Any]:
    """
    Extract satellite features for a specific field plot location and date.
    
    Args:
        latitude: Plot latitude
        longitude: Plot longitude
        date_str: Measurement date in "YYYY-MM-DD" format
        
    Returns:
        Dictionary of extracted features (NDVI, GEDI AGBD, Elevation, Rainfall, etc.)
    """
    try:
        # Define point geometry with buffer (e.g., 50m radius for field plot)
        point = ee.Geometry.Point([longitude, latitude])
        plot_geometry = point.buffer(50)
        
        # Parse date
        date = datetime.strptime(date_str, "%Y-%m-%d")
        start_date = (date - timedelta(days=30)).strftime("%Y-%m-%d")
        end_date = (date + timedelta(days=30)).strftime("%Y-%m-%d")
        year = date.year
        
        # 1. Sentinel-2 (NDVI, EVI)
        # Filter for cloud-free images near the measurement date
        s2 = ee.ImageCollection('COPERNICUS/S2_SR_HARMONIZED') \
            .filterBounds(plot_geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.lt('CLOUDY_PIXEL_PERCENTAGE', 20)) \
            .median() # Use median to remove remaining clouds/shadows
            
        # Select bands for indices
        nir = s2.select('B8').divide(10000)
        red = s2.select('B4').divide(10000)
        blue = s2.select('B2').divide(10000)
        
        # Calculate indices
        ndvi = nir.subtract(red).divide(nir.add(red)).rename('ndvi')
        evi = nir.subtract(red).divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1)).multiply(2.5).rename('evi')
        
        # 2. GEDI L4A (Biomass) - 6 month window to find nearest shot
        gedi_start = (date - timedelta(days=180)).strftime("%Y-%m-%d")
        gedi_end = (date + timedelta(days=180)).strftime("%Y-%m-%d")
        
        gedi = ee.ImageCollection('LARSE/GEDI/GEDI04_A_002_MONTHLY') \
            .filterBounds(plot_geometry) \
            .filterDate(gedi_start, gedi_end) \
            .select('agbd') \
            .mean() \
            .rename('gedi_agbd')

        gedi_rh98 = ee.ImageCollection('LARSE/GEDI/GEDI02_A_002_MONTHLY') \
            .filterBounds(plot_geometry) \
            .filterDate(gedi_start, gedi_end) \
            .select('rh98') \
            .mean() \
            .rename('gedi_rh98')
            
        # 3. Terrain (SRTM)
        srtm = ee.Image('USGS/SRTMGL1_003')
        elevation = srtm.select('elevation')
        slope = ee.Terrain.slope(elevation).rename('slope')
        aspect = ee.Terrain.aspect(elevation).rename('aspect')
        
        # 4. Topographic Wetness Index (TWI) - Proxy using Slope and Flow Accumulation
        # (Simplified approximation or use standard TWI dataset if available. For now, skip or use HydroSHEDS)
        # Using HydroSHEDS for flow accumulation if needed, but let's stick to simple terrain for V1
        
        # 5. Climate (CHIRPS Rainfall) - Annual sum for the measurement year
        rainfall = ee.ImageCollection('UCSB-CHG/CHIRPS/DAILY') \
            .filterDate(f'{year}-01-01', f'{year}-12-31') \
            .select('precipitation') \
            .sum() \
            .rename('rainfall_annual')

        # 6. Sentinel-1 SAR (structure signal, cloud-independent)
        s1 = ee.ImageCollection('COPERNICUS/S1_GRD') \
            .filterBounds(plot_geometry) \
            .filterDate(start_date, end_date) \
            .filter(ee.Filter.eq('instrumentMode', 'IW')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VV')) \
            .filter(ee.Filter.listContains('transmitterReceiverPolarisation', 'VH')) \
            .select(['VV', 'VH']) \
            .median()

        # 7. ERA5-Land monthly aggregates (temperature and total precipitation)
        era5 = ee.ImageCollection('ECMWF/ERA5_LAND/MONTHLY_AGGR') \
            .filterDate(f'{year}-01-01', f'{year}-12-31')
        era_temp = era5.select('temperature_2m').mean().rename('era5_temp_2m')
        era_precip = era5.select('total_precipitation_sum').sum().rename('era5_total_precip')

        # Canopy cover proxy: NDVI threshold fraction (0-100)
        canopy_cover = ndvi.gt(0.5).rename('canopy_cover')
            
        # Combine all features into one image for reduction
        features_image = ee.Image.cat([
            ndvi, evi, gedi, gedi_rh98, elevation, slope, aspect, rainfall, s1, era_temp, era_precip, canopy_cover
        ])
        
        # Reduce region to get mean values for the plot
        # Use bestEffort=True to handle scale differences
        stats = features_image.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=plot_geometry,
            scale=10, # Sentinel-2 resolution
            maxPixels=1e9,
            bestEffort=True
        ).getInfo()
        
        # Handle potential missing values (e.g. no GEDI shots)
        return {
            "ndvi_mean": stats.get('ndvi'),
            "evi_mean": stats.get('evi'),
            "gedi_agbd_raw": stats.get('gedi_agbd'),
            "gedi_rh98": stats.get('gedi_rh98'),
            "elevation": stats.get('elevation'),
            "slope": stats.get('slope'),
            "aspect": stats.get('aspect'),
            "rainfall_annual": stats.get('rainfall_annual'),
            "s1_vv": stats.get('VV'),
            "s1_vh": stats.get('VH'),
            "era5_temp_2m": stats.get('era5_temp_2m'),
            "era5_total_precip": stats.get('era5_total_precip'),
            "canopy_cover": (stats.get('canopy_cover') or 0.0) * 100.0 if stats.get('canopy_cover') is not None else None,
            # Add metadata
            "extraction_date": datetime.now().isoformat(),
            "feature_version": "india_v1",
            "extraction_mode": "extract_only_streaming",
        }
        
    except Exception as e:
        print(f"Error extracting features for plot ({latitude}, {longitude}): {e}")
        return {}

def extract_features_batch(
    plots: List[Dict[str, Any]],
    max_workers: int = 4,
) -> List[Dict[str, Any]]:
    """
    Extract features for a batch of plots.
    Uses bounded concurrency to reduce wall-clock time without loading
    full datasets locally.
    """
    if not plots:
        return []

    workers = max(1, min(max_workers, 8))
    results: List[Dict[str, Any]] = [None] * len(plots)  # type: ignore

    def _run(index: int, plot: Dict[str, Any]) -> Dict[str, Any]:
        features = extract_features_for_plot(
            plot['latitude'],
            plot['longitude'],
            plot['measurement_date'],
        )
        return {**plot, "features": features}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(_run, idx, plot): idx
            for idx, plot in enumerate(plots)
        }
        for future in as_completed(futures):
            idx = futures[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                plot = plots[idx]
                print(f"Batch extraction failed for plot {idx}: {e}")
                results[idx] = {**plot, "features": {}}

    return results
