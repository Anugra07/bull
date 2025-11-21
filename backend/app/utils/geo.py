from shapely.geometry import shape, Polygon, MultiPolygon, mapping
from shapely.validation import make_valid
from typing import Any, Tuple, List
from pyproj import Geod

geod = Geod(ellps="WGS84")

def normalize_geometry(geojson: Any) -> dict:
    if isinstance(geojson, dict) and geojson.get("type") == "Feature":
        return geojson["geometry"]
    return geojson


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
