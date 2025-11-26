import os
import sys
import json

# Manually load .env
env_path = os.path.join(os.getcwd(), 'backend', '.env')
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                os.environ[key] = value

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.gee import analyze_polygon, init_gee
from app.services.carbon import compute_carbon

# User's Amazon GeoJSON
geojson = {
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "name": "Amazon Rainforest - Acre, Brazil"
      },
      "geometry": {
        "type": "Polygon",
        "coordinates": [
          [
            [-67.835000, -9.964000],
            [-67.815000, -9.964000],
            [-67.815000, -9.984000],
            [-67.835000, -9.984000],
            [-67.835000, -9.964000]
          ]
        ]
      }
    }
  ]
}

def run_debug():
    print("Initializing GEE...")
    if not init_gee():
        print("Failed to init GEE. Check env vars.")
        return

    print("Running analysis...")
    try:
        results = analyze_polygon(geojson)
        print("\n--- METRICS ---")
        print(json.dumps(results, indent=2))
        
        # Compute Carbon
        print("\nComputing Carbon...")
        # Calculate area (approx 400ha)
        # Using shapely to be accurate
        from app.utils.geo import clean_and_validate, normalize_geometry
        
        # Normalize geometry first (handle FeatureCollection)
        geom_dict = normalize_geometry(geojson)
        _, area_m2, _ = clean_and_validate(geom_dict)
        print(f"Area: {area_m2} m2")
        
        carbon_results, risks = compute_carbon(results, area_m2)
        print("\n--- CARBON RESULTS ---")
        print(json.dumps(carbon_results, indent=2))
        print("\n--- RISKS ---")
        print(json.dumps(risks, indent=2))
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_debug()
