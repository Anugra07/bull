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
from app.utils.geo import clean_and_validate, normalize_geometry

# Test polygons for verification
test_polygons = {
    "Test 1: Acre Amazon (Original)": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Amazon Rainforest - Acre, Brazil"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-67.835000, -9.964000],
                    [-67.815000, -9.964000],
                    [-67.815000, -9.984000],
                    [-67.835000, -9.984000],
                    [-67.835000, -9.964000]
                ]]
            }
        }]
    },
    "Test 2: Manaus Core Rainforest": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Manaus Core - Dense Rainforest"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-60.10, -3.10],
                    [-60.05, -3.10],
                    [-60.05, -3.15],
                    [-60.10, -3.15],
                    [-60.10, -3.10]
                ]]
            }
        }]
    },
    "Test 3: Mamirauá Reserve": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Mamirauá Sustainable Development Reserve"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-64.85, -3.00],
                    [-64.80, -3.00],
                    [-64.80, -3.05],
                    [-64.85, -3.05],
                    [-64.85, -3.00]
                ]]
            }
        }]
    },
    "Test 4: Arc of Deforestation": {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"name": "Arc of Deforestation - Degraded Area"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[
                    [-54.95, -12.50],
                    [-54.90, -12.50],
                    [-54.90, -12.55],
                    [-54.95, -12.55],
                    [-54.95, -12.50]
                ]]
            }
        }]
    }
}

def run_verification():
    print("="*80)
    print("VERIFICATION TEST SUITE - Amazon Polygons")
    print("="*80)
    print()
    
    if not init_gee():
        print("❌ Failed to init GEE. Check env vars.")
        return
    
    results_summary = []
    
    for test_name, geojson in test_polygons.items():
        print(f"\n{'='*80}")
        print(f"🧪 {test_name}")
        print(f"{'='*80}\n")
        
        try:
            # Run analysis
            print("Running GEE analysis...")
            metrics = analyze_polygon(geojson)
            
            # Calculate area
            geom_dict = normalize_geometry(geojson)
            _, area_m2, _ = clean_and_validate(geom_dict)
            
            # Compute carbon
            carbon_results, risks = compute_carbon(metrics, area_m2)
            
            # Extract key metrics
            summary = {
                "test": test_name,
                "land_cover": metrics.get('land_cover'),
                "ecosystem": carbon_results.get('ecosystem_type'),
                "biomass_t_ha": metrics.get('biomass'),
                "canopy_height_m": metrics.get('canopy_height'),
                "ndvi": metrics.get('ndvi'),
                "rainfall_mm": metrics.get('rainfall'),
                "bulk_density_g_cm3": metrics.get('bulk_density'),
                "soc_tC_ha": metrics.get('soc'),
                "pixel_count": metrics.get('pixel_count'),
                "cloud_coverage_pct": metrics.get('cloud_coverage_percent'),
                "gedi_shots": metrics.get('gedi_shot_count'),
                "sequestration_rate": risks.get('sequestration_rate'),
                "annual_co2_tCO2e": carbon_results.get('annual_co2'),
                "confidence_score": metrics.get('data_confidence_score')
            }
            
            results_summary.append(summary)
            
            # Print summary
            print(f"\n📊 RESULTS SUMMARY:")
            print(f"  Land Cover: {summary['land_cover']}")
            print(f"  Ecosystem: {summary['ecosystem']}")
            print(f"  Biomass: {summary['biomass_t_ha']:.2f} t/ha")
            print(f"  Canopy Height: {summary['canopy_height_m']:.2f} m")
            print(f"  NDVI: {summary['ndvi']:.3f}")
            print(f"  Rainfall: {summary['rainfall_mm']:.1f} mm/yr")
            print(f"  Bulk Density: {summary['bulk_density_g_cm3']:.2f} g/cm³")
            print(f"  SOC: {summary['soc_tC_ha']:.2f} tC/ha")
            print(f"  Pixel Count: {summary['pixel_count']}")
            print(f"  Cloud Coverage: {summary['cloud_coverage_pct']:.1f}%")
            print(f"  GEDI Shots: {summary['gedi_shots']}")
            print(f"  Sequestration Rate: {summary['sequestration_rate']:.1f} tCO2e/ha/yr")
            print(f"  Annual CO2: {summary['annual_co2_tCO2e']:.1f} tCO2e/yr")
            print(f"  Confidence: {summary['confidence_score']:.0f}%")
            
            # Status indicators
            print(f"\n✅ STATUS CHECKS:")
            if summary['biomass_t_ha'] > 100:
                print(f"  ✅ Biomass: GOOD (>100 t/ha)")
            elif summary['biomass_t_ha'] > 50:
                print(f"  ⚠️  Biomass: MODERATE (50-100 t/ha)")
            else:
                print(f"  ❌ Biomass: LOW (<50 t/ha)")
            
            if summary['bulk_density_g_cm3'] > 0:
                print(f"  ✅ Bulk Density: WORKING ({summary['bulk_density_g_cm3']:.2f} g/cm³)")
            else:
                print(f"  ❌ Bulk Density: BROKEN (0)")
            
            if summary['cloud_coverage_pct'] < 50:
                print(f"  ✅ Cloud Coverage: GOOD (<50%)")
            else:
                print(f"  ⚠️  Cloud Coverage: HIGH (>50%)")
            
            if summary['pixel_count'] > 1000:
                print(f"  ✅ Pixel Count: GOOD (>{summary['pixel_count']})")
            else:
                print(f"  ❌ Pixel Count: LOW (<1000)")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
    
    # Final comparison table
    print(f"\n\n{'='*80}")
    print("📋 COMPARISON TABLE")
    print(f"{'='*80}\n")
    
    print(f"{'Test':<35} {'Biomass':<12} {'Height':<10} {'NDVI':<8} {'Seq.Rate':<10} {'BD':<8}")
    print(f"{'-'*35} {'-'*12} {'-'*10} {'-'*8} {'-'*10} {'-'*8}")
    
    for s in results_summary:
        test_short = s['test'].split(':')[0]
        print(f"{test_short:<35} {s['biomass_t_ha']:>8.1f} t/ha {s['canopy_height_m']:>6.1f} m {s['ndvi']:>6.3f} {s['sequestration_rate']:>6.1f} {s['bulk_density_g_cm3']:>6.2f}")
    
    print(f"\n{'='*80}")
    print("🎯 DIAGNOSTIC CONCLUSION")
    print(f"{'='*80}\n")
    
    # Check if all tests show low biomass
    all_low = all(s['biomass_t_ha'] < 50 for s in results_summary)
    any_high = any(s['biomass_t_ha'] > 200 for s in results_summary)
    
    if any_high:
        print("✅ SYSTEM WORKING: At least one polygon shows high biomass (>200 t/ha)")
        print("   → Low biomass in other areas likely reflects real degradation")
    elif all_low:
        print("⚠️  GEDI EXTRACTION ISSUE: All polygons show low biomass (<50 t/ha)")
        print("   → This suggests a systematic problem with GEDI data extraction")
        print("   → Check GEDI band selection, scale, or date filtering")
    else:
        print("⚠️  MIXED RESULTS: Some areas show moderate biomass (50-200 t/ha)")
        print("   → May indicate regional variation or partial GEDI coverage")
    
    # Check bulk density
    all_bd_working = all(s['bulk_density_g_cm3'] > 0 for s in results_summary)
    if all_bd_working:
        print("✅ BULK DENSITY: Fixed - all polygons return valid values")
    else:
        print("❌ BULK DENSITY: Still broken - some polygons return 0")
    
    # Check cloud coverage
    avg_cloud = sum(s['cloud_coverage_pct'] for s in results_summary) / len(results_summary)
    if avg_cloud < 50:
        print(f"✅ CLOUD COVERAGE: Improved - average {avg_cloud:.1f}% (was 99.6%)")
    else:
        print(f"⚠️  CLOUD COVERAGE: Still high - average {avg_cloud:.1f}%")

if __name__ == "__main__":
    run_verification()
