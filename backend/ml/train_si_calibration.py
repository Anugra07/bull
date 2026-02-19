"""
Stocking Index (SI) → Biomass Calibration Model Trainer.

Trains ecosystem-specific Random Forest models using Verra VM0047
monitoring data where projects have calibrated their stocking index
against field-measured biomass. This is high-quality training data
because VM0047 requires this calibration.

Usage:
    python backend/ml/train_si_calibration.py
"""

import os
import sys
import json
from datetime import datetime, timezone
import numpy as np
import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import cross_val_score, train_test_split
from sklearn.metrics import mean_squared_error, r2_score

sys.path.append(os.path.join(os.getcwd(), 'backend'))

from dotenv import load_dotenv
load_dotenv('backend/.env')

try:
    from supabase import create_client, Client
except ImportError:
    Client = None
    create_client = None


# Supabase
url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
supabase = None
if url and key:
    try:
        supabase = create_client(url, key)
    except:
        pass

ECOSYSTEMS = ['tropical_forest', 'temperate_forest', 'grassland', 'mangrove', 'plantation', 'reforestation']

FEATURE_COLUMNS = ['ndvi', 'evi', 'gedi_rh98', 'canopy_cover', 'elevation', 'slope', 'rainfall_annual']


def fetch_verra_training_data() -> pd.DataFrame:
    """
    Fetch Verra monitoring data with GEE features from Supabase.
    Returns flattened DataFrame ready for training.
    """
    if not supabase:
        return None
    
    try:
        response = supabase.table("verra_monitoring_data") \
            .select("*, verra_projects(ecosystem_type, country)") \
            .not_.is_("gee_features", "null") \
            .not_.is_("plot_data", "null") \
            .execute()
        
        data = response.data
        if not data:
            return None
        
        records = []
        for row in data:
            gee = row.get('gee_features', {})
            plots = row.get('plot_data', [])
            project = row.get('verra_projects', {})
            ecosystem = project.get('ecosystem_type', 'unknown')
            
            # Each plot becomes a training sample
            for plot in plots:
                if 'biomass' not in plot:
                    continue
                record = {
                    'field_measured_biomass': plot['biomass'],
                    'ecosystem': ecosystem,
                    'ndvi': gee.get('ndvi_mean', 0),
                    'evi': gee.get('evi_mean', 0),
                    'gedi_rh98': gee.get('gedi_rh98', 0),
                    'canopy_cover': gee.get('canopy_cover', 0),
                    'elevation': gee.get('elevation', 0),
                    'slope': gee.get('slope', 0),
                    'rainfall_annual': gee.get('rainfall_annual', 0),
                }
                records.append(record)
        
        return pd.DataFrame(records) if records else None
    except Exception as e:
        print(f"Error fetching Verra data: {e}")
        return None


def generate_mock_si_data() -> pd.DataFrame:
    """Generate synthetic ecosystem-specific SI→Biomass data for pipeline testing."""
    print("Generating mock SI calibration data...")
    np.random.seed(55)
    
    records = []
    
    # Ecosystem-specific data generation
    eco_configs = {
        'tropical_forest': {
            'n': 200, 'ndvi_range': (0.6, 0.95), 'biomass_base': 150,
            'biomass_scale': 200, 'rainfall_range': (1500, 3500)
        },
        'temperate_forest': {
            'n': 150, 'ndvi_range': (0.4, 0.85), 'biomass_base': 80,
            'biomass_scale': 150, 'rainfall_range': (600, 1500)
        },
        'grassland': {
            'n': 100, 'ndvi_range': (0.2, 0.6), 'biomass_base': 5,
            'biomass_scale': 40, 'rainfall_range': (300, 1000)
        },
        'mangrove': {
            'n': 80, 'ndvi_range': (0.5, 0.85), 'biomass_base': 100,
            'biomass_scale': 180, 'rainfall_range': (1000, 2500)
        },
        'plantation': {
            'n': 120, 'ndvi_range': (0.5, 0.9), 'biomass_base': 60,
            'biomass_scale': 120, 'rainfall_range': (800, 2000)
        },
    }
    
    for eco, cfg in eco_configs.items():
        n = cfg['n']
        ndvi = np.random.uniform(*cfg['ndvi_range'], n)
        evi = ndvi * np.random.uniform(0.5, 0.8, n)
        elevation = np.random.uniform(0, 1500, n)
        slope = np.random.uniform(0, 25, n)
        rainfall = np.random.uniform(*cfg['rainfall_range'], n)
        canopy_cover = np.clip(ndvi * 100 + np.random.normal(0, 10, n), 0, 100)
        gedi_rh98 = np.random.uniform(5, 35, n)
        
        # Biomass = f(NDVI, canopy cover, rainfall, gedi_rh98)
        biomass = (
            cfg['biomass_base']
            + cfg['biomass_scale'] * ndvi
            + 0.5 * gedi_rh98
            + 0.01 * rainfall
            + np.random.normal(0, 15, n)
        ).clip(min=0)
        
        for i in range(n):
            records.append({
                'field_measured_biomass': biomass[i],
                'ecosystem': eco,
                'ndvi': ndvi[i],
                'evi': evi[i],
                'gedi_rh98': gedi_rh98[i],
                'canopy_cover': canopy_cover[i],
                'elevation': elevation[i],
                'slope': slope[i],
                'rainfall_annual': rainfall[i],
            })
    
    return pd.DataFrame(records)


def train_si_models():
    """Train ecosystem-specific SI → Biomass calibration models."""
    
    # Try real data
    df = fetch_verra_training_data()
    
    if df is None or len(df) < 20:
        print("Insufficient Verra data. Using mock data for pipeline testing.")
        df = generate_mock_si_data()
    
    print(f"Total training samples: {len(df)}")
    print(f"Ecosystems: {df['ecosystem'].value_counts().to_dict()}")
    
    si_models = {}
    results_summary = []
    
    for ecosystem in df['ecosystem'].unique():
        eco_data = df[df['ecosystem'] == ecosystem]
        
        if len(eco_data) < 10:
            print(f"  {ecosystem}: Skipping (only {len(eco_data)} samples)")
            continue
        
        # Prepare features
        available_features = [f for f in FEATURE_COLUMNS if f in eco_data.columns]
        X = eco_data[available_features].fillna(0)
        y = eco_data['field_measured_biomass']
        
        # Cross-validation
        rf = RandomForestRegressor(n_estimators=200, random_state=42, max_depth=15)
        cv_scores = cross_val_score(rf, X, y, scoring='neg_mean_squared_error', cv=min(5, len(eco_data) // 3))
        cv_rmse = np.sqrt(-cv_scores.mean())
        
        # Train on full data
        rf.fit(X, y)
        
        # Feature importance
        importance = dict(zip(available_features, rf.feature_importances_))
        top_features = sorted(importance.items(), key=lambda x: x[1], reverse=True)[:3]
        
        print(f"  {ecosystem}: RMSE={cv_rmse:.2f} t/ha | n={len(eco_data)} | Top features: {top_features}")
        
        si_models[ecosystem] = {
            'model': rf,
            'features': available_features,
            'cv_rmse': cv_rmse,
            'n_samples': len(eco_data),
        }
        
        results_summary.append({
            'ecosystem': ecosystem,
            'rmse': round(cv_rmse, 2),
            'r2': round(rf.score(X, y), 3),
            'n_samples': len(eco_data),
        })
    
    # Save ensemble
    model_dir = os.path.join(os.getcwd(), 'backend', 'ml', 'models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'stocking_index_calibrated_v1.pkl')
    joblib.dump(si_models, model_path)

    meta_path = os.path.join(model_dir, 'stocking_index_calibrated_v1.meta.json')
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "version": "stocking_index_calibrated_v1",
                "trained_at": datetime.now(timezone.utc).isoformat(),
                "ecosystems": [
                    {
                        "ecosystem": r["ecosystem"],
                        "rmse": r["rmse"],
                        "r2": r["r2"],
                        "n_samples": r["n_samples"],
                    }
                    for r in results_summary
                ],
                "policy": "open_public_no_personal_iot",
                "geo_scope": "india_first",
            },
            f,
            indent=2,
        )
    
    print(f"\n{'='*60}")
    print(f"Saved {len(si_models)} ecosystem-specific SI models to {model_path}")
    print(f"Saved SI metadata to {meta_path}")
    print(f"\nSummary:")
    for r in results_summary:
        print(f"  {r['ecosystem']:20s} | RMSE: {r['rmse']:6.2f} t/ha | R²: {r['r2']:.3f} | n={r['n_samples']}")
    
    return si_models


if __name__ == "__main__":
    train_si_models()
