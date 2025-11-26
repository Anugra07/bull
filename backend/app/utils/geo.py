from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.validation import make_valid
from typing import Any, Tuple, List
from pyproj import Geod

geod = Geod(ellps="WGS84")

def normalize_geometry(geom_input: Any) -> Any:
    """
    Accept GeoJSON Feature, FeatureCollection, or raw Geometry dict.
    Returns a geometry dict suitable for shapely.
    """
    if isinstance(geom_input, dict):
        geom_type = geom_input.get("type", "").lower()
        
        # Handle FeatureCollection - extract first feature's geometry
        if geom_type == "featurecollection":
            features = geom_input.get("features", [])
            if not features or len(features) == 0:
                raise ValueError("FeatureCollection has no features")
            # Get first feature's geometry
            first_feature = features[0]
            if isinstance(first_feature, dict) and first_feature.get("type") == "Feature":
                return first_feature.get("geometry")
            return first_feature
        
        # Handle Feature - extract geometry
        if geom_type == "feature":
            return geom_input.get("geometry")
        
        # Already a geometry (polygon, multipolygon, etc.)
        if geom_type in ["polygon", "multipolygon", "point", "linestring", "multipoint", "multilinestring"]:
            return geom_input
        
        raise ValueError(f"Unknown geometry type: '{geom_type}'")
    
    return geom_input


def clean_and_validate(geojson_geom: Any) -> Tuple[MultiPolygon | Polygon, float, List[float]]:
    geom = shape(geojson_geom)
    geom = make_valid(geom)

    if not isinstance(geom, (Polygon, MultiPolygon)):
        raise ValueError("Geometry must be Polygon or MultiPolygon")

    # Compute geodesic area in m^2 using pyproj.Geod
    def polygon_area(g: Polygon) -> float:
        lon, lat = g.exterior.coords.xy
        area, _ = geod.polygon_area_perimeter(lon, lat)
        return abs(area)  # area can be negative by orientation

    total_area = 0.0
    if isinstance(geom, Polygon):
        total_area = polygon_area(geom)
    else:
        for g in geom.geoms:
            total_area += polygon_area(g)

    minx, miny, maxx, maxy = geom.bounds
    bbox = [minx, miny, maxx, maxy]

    return geom, float(total_area), bbox


def to_geojson(geom: Polygon | MultiPolygon) -> dict:
    return mapping(geom)
