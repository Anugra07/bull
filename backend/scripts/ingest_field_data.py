import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd

# Add backend directory to path to import app modules if needed
sys.path.append(os.path.join(os.getcwd(), 'backend'))

try:
    from supabase import create_client, Client
except ImportError:
    create_client = None  # type: ignore[assignment]
    Client = Any  # type: ignore[assignment]


PUBLIC_DATA_POLICY = {
    "gedi-fia": {
        "dataset_name": "GEDI-FIA",
        "license": "Public research data",
        "provider": "ORNL DAAC",
    },
    "china-agb": {
        "dataset_name": "China-30m-AGB",
        "license": "Open scientific dataset",
        "provider": "Zenodo/Nature",
    },
    "biomassters": {
        "dataset_name": "BioMassters",
        "license": "Competition dataset",
        "provider": "Radiant Earth",
    },
}

POLICY_TAG = "open_public_no_personal_iot"
INDIA_BOUNDS = {
    "lat_min": 6.0,
    "lat_max": 38.5,
    "lon_min": 68.0,
    "lon_max": 98.0,
}


def get_supabase_client() -> Client:
    if create_client is None:
        raise RuntimeError(
            "supabase-py not found. Install requirements or run with --dry-run for local validation."
        )

    url: Optional[str] = os.environ.get("SUPABASE_URL")
    key: Optional[str] = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        from dotenv import load_dotenv

        load_dotenv('backend/.env')
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")

    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set for ingestion"
        )

    return create_client(url, key)


def validate_source_policy(source: str) -> Dict[str, str]:
    source_key = source.lower().strip()
    if source_key not in PUBLIC_DATA_POLICY:
        raise ValueError(f"Source '{source}' is not approved under open/public policy")
    return PUBLIC_DATA_POLICY[source_key]


def iter_dataset_chunks(
    file_path: str,
    desired_columns: List[str],
    chunksize: int,
) -> Iterable[pd.DataFrame]:
    if not os.path.exists(file_path):
        raise FileNotFoundError(file_path)

    lower = file_path.lower()
    if lower.endswith('.csv'):
        reader = pd.read_csv(
            file_path,
            chunksize=chunksize,
            usecols=lambda c: c in desired_columns,
            low_memory=False,
        )
        yield from reader
        return

    if lower.endswith('.tsv'):
        reader = pd.read_csv(
            file_path,
            sep='\t',
            chunksize=chunksize,
            usecols=lambda c: c in desired_columns,
            low_memory=False,
        )
        yield from reader
        return

    if lower.endswith('.parquet') or lower.endswith('.pq'):
        # Parquet is columnar; pull only relevant columns and yield once.
        try:
            available = pd.read_parquet(file_path, columns=[c for c in desired_columns]).copy()
        except Exception:
            available = pd.read_parquet(file_path).copy()
            keep = [c for c in desired_columns if c in available.columns]
            if keep:
                available = available[keep]
        yield available
        return

    raise ValueError(f"Unsupported file format for {file_path}")


def first_value(row: pd.Series, keys: List[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and pd.notna(row[key]):
            return row[key]
    return default


def parse_date(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return datetime.now(timezone.utc).date().isoformat()

    try:
        ts = pd.to_datetime(value, utc=True, errors='coerce')
        if pd.isna(ts):
            return datetime.now(timezone.utc).date().isoformat()
        return ts.date().isoformat()
    except Exception:
        return datetime.now(timezone.utc).date().isoformat()


def in_india(lat: float, lon: float) -> bool:
    return (
        INDIA_BOUNDS["lat_min"] <= lat <= INDIA_BOUNDS["lat_max"]
        and INDIA_BOUNDS["lon_min"] <= lon <= INDIA_BOUNDS["lon_max"]
    )


def build_common_record(
    row: pd.Series,
    source: str,
    policy_meta: Dict[str, str],
    biomass_keys: List[str],
    ecosystem_default: str,
    india_only: bool,
) -> Optional[Dict[str, Any]]:
    lat = first_value(row, ["lat", "latitude", "Latitude", "Lat", "y", "Y"])
    lon = first_value(row, ["lon", "lng", "longitude", "Longitude", "Long", "Lon", "x", "X"])
    agb = first_value(row, biomass_keys)

    if lat is None or lon is None or agb is None:
        return None

    try:
        lat_f = float(lat)
        lon_f = float(lon)
        agb_f = float(agb)
    except Exception:
        return None

    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return None

    if india_only and not in_india(lat_f, lon_f):
        return None

    climate_zone = "Tropical" if abs(lat_f) < 23.5 else "Temperate"

    return {
        "dataset_name": policy_meta["dataset_name"],
        "latitude": lat_f,
        "longitude": lon_f,
        "biomass_agb": max(0.0, agb_f),
        "measurement_date": parse_date(first_value(row, ["date", "measurement_date", "timestamp", "year"])),
        "ecosystem_type": first_value(row, ["ecosystem", "ecosystem_type", "land_cover"], ecosystem_default),
        "climate_zone": first_value(row, ["climate_zone"], climate_zone),
        "features": {
            "provenance": {
                "source": source,
                "provider": policy_meta["provider"],
                "license": policy_meta["license"],
                "policy": POLICY_TAG,
                "ingested_at": datetime.now(timezone.utc).isoformat(),
                "extraction_mode": "stream_extract_no_full_download",
            }
        },
    }


def batch_insert_records(
    supabase: Client,
    records: List[Dict[str, Any]],
    batch_size: int = 200,
    dry_run: bool = False,
) -> int:
    total = len(records)
    if total == 0:
        return 0

    if dry_run:
        return total

    for i in range(0, total, batch_size):
        batch = records[i : i + batch_size]
        supabase.table("field_plots").insert(batch).execute()

    return total


def ingest_source(
    source: str,
    file_path: str,
    supabase: Client,
    biomass_keys: List[str],
    ecosystem_default: str,
    desired_columns: List[str],
    chunksize: int,
    india_only: bool,
    dry_run: bool,
) -> None:
    policy_meta = validate_source_policy(source)
    print(f"Ingesting {source} from {file_path} | india_only={india_only} | chunksize={chunksize}")

    inserted = 0
    scanned_rows = 0

    for chunk in iter_dataset_chunks(file_path, desired_columns, chunksize):
        scanned_rows += len(chunk)
        records: List[Dict[str, Any]] = []

        for _, row in chunk.iterrows():
            record = build_common_record(
                row=row,
                source=source,
                policy_meta=policy_meta,
                biomass_keys=biomass_keys,
                ecosystem_default=ecosystem_default,
                india_only=india_only,
            )
            if record:
                records.append(record)

        inserted += batch_insert_records(supabase, records, dry_run=dry_run)
        print(f"chunk processed | scanned={scanned_rows} | accepted={inserted}")

    print(f"Done: scanned={scanned_rows}, inserted={inserted}, dry_run={dry_run}")


def ingest_gedi_fia(file_path: str, supabase: Client, chunksize: int, india_only: bool, dry_run: bool) -> None:
    ingest_source(
        source="gedi-fia",
        file_path=file_path,
        supabase=supabase,
        biomass_keys=["agbd", "agbd_t_ha", "biomass_agb", "AGBD", "AGB"],
        ecosystem_default="Forest",
        desired_columns=[
            "lat", "latitude", "Latitude", "Lat", "y", "Y",
            "lon", "lng", "longitude", "Longitude", "Long", "Lon", "x", "X",
            "agbd", "agbd_t_ha", "biomass_agb", "AGBD", "AGB",
            "date", "measurement_date", "timestamp", "year",
            "ecosystem", "ecosystem_type", "land_cover", "climate_zone",
        ],
        chunksize=chunksize,
        india_only=india_only,
        dry_run=dry_run,
    )


def ingest_china_agb(file_path: str, supabase: Client, chunksize: int, india_only: bool, dry_run: bool) -> None:
    ingest_source(
        source="china-agb",
        file_path=file_path,
        supabase=supabase,
        biomass_keys=["agb", "AGB", "biomass", "biomass_agb", "agb_t_ha"],
        ecosystem_default="Forest",
        desired_columns=[
            "lat", "latitude", "Latitude", "Lat", "y", "Y",
            "lon", "lng", "longitude", "Longitude", "Long", "Lon", "x", "X",
            "agb", "AGB", "biomass", "biomass_agb", "agb_t_ha",
            "date", "measurement_date", "timestamp", "year",
            "ecosystem", "ecosystem_type", "land_cover", "climate_zone",
        ],
        chunksize=chunksize,
        india_only=india_only,
        dry_run=dry_run,
    )


def ingest_biomassters(file_path: str, supabase: Client, chunksize: int, india_only: bool, dry_run: bool) -> None:
    ingest_source(
        source="biomassters",
        file_path=file_path,
        supabase=supabase,
        biomass_keys=["biomass", "biomass_agb", "target", "label", "agb"],
        ecosystem_default="Forest",
        desired_columns=[
            "lat", "latitude", "Latitude", "Lat", "y", "Y",
            "lon", "lng", "longitude", "Longitude", "Long", "Lon", "x", "X",
            "biomass", "biomass_agb", "target", "label", "agb",
            "date", "measurement_date", "timestamp", "year",
            "ecosystem", "ecosystem_type", "land_cover", "climate_zone",
        ],
        chunksize=chunksize,
        india_only=india_only,
        dry_run=dry_run,
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Ingest field plot data to Supabase")
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        choices=["gedi-fia", "china-agb", "biomassters"],
        help="Dataset source name",
    )
    parser.add_argument("--file", type=str, required=True, help="Path to the local CSV/Parquet file")
    parser.add_argument("--chunksize", type=int, default=50000, help="Chunk size for streaming ingestion")
    parser.add_argument("--global", dest="india_only", action="store_false", help="Disable India-only filtering")
    parser.add_argument("--dry-run", action="store_true", help="Parse and filter without writing to Supabase")
    parser.set_defaults(india_only=True)

    args = parser.parse_args()

    sb = get_supabase_client()

    if args.source == "gedi-fia":
        ingest_gedi_fia(args.file, sb, args.chunksize, args.india_only, args.dry_run)
    elif args.source == "china-agb":
        ingest_china_agb(args.file, sb, args.chunksize, args.india_only, args.dry_run)
    elif args.source == "biomassters":
        ingest_biomassters(args.file, sb, args.chunksize, args.india_only, args.dry_run)
