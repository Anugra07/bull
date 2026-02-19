import os
import sys
import json
from datetime import datetime, timezone
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, GridSearchCV
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
    # Try loading from .env
    from dotenv import load_dotenv
    load_dotenv('backend/.env')
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key or create_client is None:
    print("Warning: Supabase unavailable. Using MOCK data.")
    supabase = None
else:
    supabase: Client = create_client(url, key)

def fetch_training_data():
    """Fetch field plot data and features from Supabase."""
    if not supabase:
        return None
    
    try:
        # Fetch data where features are populated
        response = supabase.table("field_plots") \
            .select("id, biomass_agb, features, ecosystem_type, climate_zone, latitude") \
            .not_.is_("features", "null") \
            .execute()
        
        data = response.data
        if not data:
            print("No training data found in Supabase.")
            return None
            
        # Convert to DataFrame
        records = []
        for row in data:
            features = row.get('features', {})
            if not features: continue
            
            record = {
                'biomass_agb_measured': row['biomass_agb'],
                'ecosystem': row['ecosystem_type'],
                'climate_zone': row['climate_zone'],
                'latitude': row['latitude'],
                # Flatten features
                'gedi_agbd_raw': features.get('gedi_agbd_raw'),
                'ndvi_mean': features.get('ndvi_mean'),
                'evi_mean': features.get('evi_mean'),
                'elevation': features.get('elevation'),
                'slope': features.get('slope'),
                'rainfall_annual': features.get('rainfall_annual')
            }
            records.append(record)
            
        return pd.DataFrame(records)
        
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def generate_mock_data(n_samples=100):
    """Generate synthetic data for testing the pipeline."""
    print("Generating mock training data...")
    np.random.seed(42)
    
    data = {
        'gedi_agbd_raw': np.random.uniform(0, 300, n_samples),
        'ndvi_mean': np.random.uniform(0.2, 0.9, n_samples),
        'evi_mean': np.random.uniform(0.1, 0.7, n_samples),
        'elevation': np.random.uniform(0, 1000, n_samples),
        'slope': np.random.uniform(0, 30, n_samples),
        'rainfall_annual': np.random.uniform(500, 3000, n_samples),
        'latitude': np.random.uniform(-10, 10, n_samples),
        'ecosystem': np.random.choice(['Forest', 'Shrubland', 'Grassland'], n_samples),
        'climate_zone': np.random.choice(['Tropical', 'Temperate'], n_samples)
    }
    
    df = pd.DataFrame(data)
    
    # Simulate ground truth: GEDI underestimates by 20% on average, plus noise
    true_bias = 1.2
    noise = np.random.normal(0, 20, n_samples)
    df['biomass_agb_measured'] = df['gedi_agbd_raw'] * true_bias + noise
    df['biomass_agb_measured'] = df['biomass_agb_measured'].clip(lower=0)
    
    return df

def train_model():
    df = fetch_training_data()
    
    if df is None or len(df) < 10:
        print("Insufficient real data. Falling back to mock data for demonstration.")
        df = generate_mock_data()
    
    print(f"Training on {len(df)} samples...")
    
    # Preprocessing
    # One-hot encode categorical variables
    df_encoded = pd.get_dummies(df, columns=['ecosystem', 'climate_zone'], drop_first=True)
    
    # Handle missing values if any
    df_encoded = df_encoded.fillna(0)
    
    X = df_encoded.drop('biomass_agb_measured', axis=1)
    y = df['biomass_agb_measured']
    
    # Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    # Train Random Forest
    rf = RandomForestRegressor(n_estimators=100, random_state=42)
    rf.fit(X_train, y_train)
    
    # Evaluate
    y_pred = rf.predict(X_test)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)
    
    print(f"Model Performance:")
    print(f"RMSE: {rmse:.2f} t/ha")
    print(f"R²: {r2:.3f}")
    
    # Save model
    model_dir = os.path.join(os.getcwd(), 'backend', 'ml', 'models')
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, 'gedi_bias_v1.pkl')
    
    joblib.dump(rf, model_path)
    print(f"Model saved to {model_path}")

    # Persist deterministic feature schema + metrics for runtime alignment.
    meta_path = os.path.join(model_dir, 'gedi_bias_v1.meta.json')
    metadata = {
        "version": "gedi_bias_v1",
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
    print(f"Model metadata saved to {meta_path}")

if __name__ == "__main__":
    train_model()
