import sys
import os
import json

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.carbon import compute_carbon

def verify_ml_integration():
    print("Verifying ML Integration in carbon.py...")
    
    # Mock metrics that simulate GEE output
    mock_metrics = {
        "biomass": 100.0,
        "biomass_aboveground": 100.0,
        "biomass_belowground": 20.0,
        "biomass_total": 120.0,
        "soc": 50.0,
        "bulk_density": 1.3,
        "ndvi": 0.6,
        "evi": 0.4,
        "elevation": 500.0,
        "slope": 10.0,
        "rainfall": 1500.0,
        "latitude": 5.0,
        "land_cover": 10, # Forest
        "trend_classification": "Stable",
        "ndvi_trend": 0.01,
        "fire_burn_percent": 0.0,
        "rainfall_anomaly_percent": 0.0,
        # Features for ML
        "ndvi_mean": 0.6,
        "evi_mean": 0.4,
        "rainfall_annual": 1500.0,
        "ecosystem_type": "Forest"
    }
    
    print("\n1. Running compute_carbon with mock metrics...")
    try:
        results, risks = compute_carbon(mock_metrics, area_m2=10000.0) # 1 hectare
        
        print("\n--- Results ---")
        print(json.dumps(results, indent=2))
        print("\n--- Risks ---")
        print(json.dumps(risks, indent=2))
        
        # Check if ML models were used
        if risks.get('ml_models_used'):
            print("\n✅ SUCCESS: ML models were loaded and used!")
        else:
            print("\n❌ WARNING: ML models were NOT used (models_loaded=False).")
            # Check if models exist
            model_dir = os.path.join(os.getcwd(), 'backend', 'ml', 'models')
            print(f"Checking model directory: {model_dir}")
            print(f"Files: {os.listdir(model_dir) if os.path.exists(model_dir) else 'Directory not found'}")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_ml_integration()
