import os
import sys
import pandas as pd
from typing import List, Dict, Any
from datetime import datetime
import uuid

# Add backend directory to path to import app modules if needed
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from supabase import create_client, Client
except ImportError:
    print("supabase-py not found. Please install dependencies.")
    sys.exit(1)

# Initialize Supabase Client
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role key for writing

if not url or not key:
    print("Error: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables must be set.")
    print("Please run with: export SUPABASE_URL=... export SUPABASE_SERVICE_ROLE_KEY=... python backend/scripts/ingest_field_data.py")
    # For dev convenience, try loading from .env
    from dotenv import load_dotenv
    load_dotenv('backend/.env')
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY") # Fallback to anon (might fail RLS)


supabase: Client = create_client(url, key)

def ingest_gedi_fia(file_path: str):
    """
    Ingest GEDI-FIA Fusion dataset (ORNL DAAC).
    Expected columns: lat, lon, agbd_t_ha, date, etc.
    """
    print(f"Ingesting GEDI-FIA from {file_path}...")
    try:
        df = pd.read_csv(file_path)
        
        # Standardize columns
        records = []
        for _, row in df.iterrows():
            record = {
                "dataset_name": "GEDI-FIA",
                "latitude": row.get('lat') or row.get('latitude'),
                "longitude": row.get('lon') or row.get('longitude'),
                "biomass_agb": row.get('agbd') or row.get('biomass_agb'),
                "measurement_date": row.get('date', datetime.now().isoformat()), # Default to now if missing
                "features": {}, # Empty for now, will be populated by GEE extraction
                "ecosystem_type": "Forest", # Default for GEDI-FIA
                "climate_zone": "Temperate" # detailed logic needed
            }
            records.append(record)
            
        # Batch insert
        batch_size = 100
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            data, count = supabase.table("field_plots").insert(batch).execute()
            print(f"Inserted batch {i//batch_size + 1}/{len(records)//batch_size + 1}")
            
    except Exception as e:
        print(f"Error ingesting GEDI-FIA: {e}")

def ingest_china_agb(file_path: str):
    """Ingest China 30m AGB dataset."""
    print(f"Ingesting China AGB from {file_path}...")
    # Implementation similar to above...
    pass

def ingest_biomassters(file_path: str):
    """Ingest BioMassters training labels."""
    print(f"Ingesting BioMassters from {file_path}...")
    # Implementation similar to above...
    pass

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest field plot data to Supabase")
    parser.add_argument("--source", type=str, required=True, choices=['gedi-fia', 'china-agb', 'biomassters'], help="Dataset source name")
    parser.add_argument("--file", type=str, required=True, help="Path to the local CSV/Parquet file")
    
    args = parser.parse_args()
    
    if args.source == 'gedi-fia':
        ingest_gedi_fia(args.file)
    elif args.source == 'china-agb':
        ingest_china_agb(args.file)
    elif args.source == 'biomassters':
        ingest_biomassters(args.file)
