import os
import sys
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

# Add backend directory to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from supabase import create_client, Client
except ImportError:
    print("supabase-py not found. Falling back to mock data.")
    create_client = None
    Client = None

# Initialize Supabase Client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    from dotenv import load_dotenv
    load_dotenv('backend/.env')
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key or create_client is None:
    print("Warning: Supabase unavailable. Using MOCK data.")
    supabase = None
else:
    supabase: Client = create_client(url, key)

def fetch_soc_data():
    """Fetch SOC ground truth data from Supabase."""
    if not supabase:
        return None
    
    try:
        response = supabase.table("field_plots") \
            .select("id, soc_0_30cm, features, ecosystem_type, latitude, longitude") \
            .not_.is_("features", "null") \
            .not_.is_("soc_0_30cm", "null") \
            .execute()
        
        data = response.data
        if not data:
            print("No SOC training data found in Supabase.")
            return None
            
        records = []
        for row in data:
            features = row.get('features', {})
            if not features: continue
            
            record = {
                'soc_measured': row['soc_0_30cm'],
                'ecosystem': row['ecosystem_type'],
                'latitude': row['latitude'],
                'longitude': row['longitude'],
                'ndvi_mean': features.get('ndvi_mean'),
                'evi_mean': features.get('evi_mean'),
                'elevation': features.get('elevation'),
                'slope': features.get('slope'),
                'aspect': features.get('aspect'),
                'rainfall_annual': features.get('rainfall_annual')
            }
            records.append(record)
            
        return pd.DataFrame(records)
        
    except Exception as e:
        print(f"Error fetching SOC data: {e}")
        return None

def generate_mock_soc_data(n_samples=100):
    """Generate synthetic SOC data."""
    print("Generating mock SOC data...")
    np.random.seed(123)
    
    data = {
        'ndvi_mean': np.random.uniform(0.1, 0.8, n_samples),
        'evi_mean': np.random.uniform(0.05, 0.6, n_samples),
        'elevation': np.random.uniform(0, 2000, n_samples),
        'slope': np.random.uniform(0, 45, n_samples),
        'aspect': np.random.uniform(0, 360, n_samples),
        'rainfall_annual': np.random.uniform(300, 2500, n_samples),
        'latitude': np.random.uniform(-40, 40, n_samples),
        'ecosystem': np.random.choice(['Forest', 'Cropland', 'Grassland', 'Wetland'], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Simulate SOC: heavily dependent on ecosystem and rainfall
    soc = 30 + (df['ndvi_mean'] * 50) + (df['rainfall_annual'] / 100)
    eco_map = {'Wetland': 50, 'Forest': 20, 'Grassland': 10, 'Cropland': -10}
    soc += df['ecosystem'].map(eco_map)
    soc += np.random.normal(0, 10, n_samples)
    df['soc_measured'] = soc.clip(lower=0)
    
    return df

def train_soc_model():
    df = fetch_soc_data()
    
    if df is None or len(df) < 10:
        print("Insufficient real data. Falling back to mock data.")
        df = generate_mock_soc_data()
        
    print(f"Training SOC model on {len(df)} samples...")
    
    # Preprocessing
    df_encoded = pd.get_dummies(df, columns=['ecosystem'], drop_first=True)
    df_encoded = df_encoded.fillna(0)
    
    X = df_encoded.drop('soc_measured', axis=1)
    y = df['soc_measured']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train GradientBoosting (scikit-learn, no libomp dependency)
    gbr = GradientBoostingRegressor(
        n_estimators=200,
        learning_rate=0.05,
        max_depth=5,
        random_state=42
    )
    gbr.fit(X_train, y_train)
    
    # Evaluate
    y_pred = gbr.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"SOC Model Performance:")
    print(f"RMSE: {rmse:.2f} tC/ha")
    print(f"R²: {r2:.3f}")
    
    # Save model
    model_dir = os.path.join(os.getcwd(), 'backend', 'ml', 'models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'soc_downscaling_xgb_v1.pkl')
    
    joblib.dump(gbr, model_path)
    print(f"SOC Model saved to {model_path}")

    meta_path = os.path.join(model_dir, 'soc_downscaling_xgb_v1.meta.json')
    metadata = {
        "version": "soc_downscaling_xgb_v1",
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "n_samples": int(len(df)),
        "rmse": float(rmse),
        "r2": float(r2),
        "feature_names": [str(x) for x in list(X.columns)],
        "policy": "open_public_no_personal_iot",
        "geo_scope": "india_first",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    print(f"SOC model metadata saved to {meta_path}")

if __name__ == "__main__":
    train_soc_model()
