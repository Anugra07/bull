"""
Backfill missing field-plot feature vectors using Earth Engine extraction.

Usage:
  python backend/scripts/backfill_field_plot_features.py --limit 200
"""

import os
import sys
from datetime import datetime
from typing import Any, Dict, List

sys.path.append(os.path.join(os.getcwd(), "backend"))

from dotenv import load_dotenv
try:
    from supabase import create_client
except ImportError as e:
    raise RuntimeError("supabase-py is required for backfill_field_plot_features.py") from e

from app.services.gee import init_gee
from app.services.features import extract_features_for_plot


FEATURE_VERSION = "india_v1"
POLICY_TAG = "open_public_no_personal_iot"


def get_supabase_client():
    load_dotenv("backend/.env")
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required")
    return create_client(url, key)


def get_rows_to_backfill(sb, limit: int) -> List[Dict[str, Any]]:
    # First: explicit NULL features.
    res = (
        sb.table("field_plots")
        .select("id, latitude, longitude, measurement_date, features")
        .is_("features", "null")
        .limit(limit)
        .execute()
    )
    rows = res.data or []

    if len(rows) >= limit:
        return rows

    # Second: empty dict features.
    remaining = limit - len(rows)
    res_empty = (
        sb.table("field_plots")
        .select("id, latitude, longitude, measurement_date, features")
        .eq("features", {})
        .limit(remaining)
        .execute()
    )
    return rows + (res_empty.data or [])


def update_feature_row(sb, row_id: str, features: Dict[str, Any]) -> None:
    sb.table("field_plots").update({"features": features}).eq("id", row_id).execute()


def main(limit: int) -> None:
    if not init_gee():
        raise RuntimeError("GEE is not initialized. Check backend/.env credentials")

    sb = get_supabase_client()
    rows = get_rows_to_backfill(sb, limit)
    if not rows:
        print("No rows require feature backfill.")
        return

    print(f"Backfilling {len(rows)} rows...")

    updated = 0
    failed = 0
    for row in rows:
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            date_str = str(row.get("measurement_date") or datetime.utcnow().date().isoformat())

            extracted = extract_features_for_plot(lat, lon, date_str)
            if not extracted:
                failed += 1
                continue

            feature_doc = dict(extracted)
            feature_doc["feature_version"] = FEATURE_VERSION
            feature_doc["policy"] = POLICY_TAG
            feature_doc["backfilled_at"] = datetime.utcnow().isoformat()

            update_feature_row(sb, row["id"], feature_doc)
            updated += 1
        except Exception as e:
            failed += 1
            print(f"Failed row {row.get('id')}: {e}")

    print(f"Backfill complete. updated={updated}, failed={failed}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Backfill field_plot features from GEE")
    parser.add_argument("--limit", type=int, default=200, help="Max rows to process")
    args = parser.parse_args()

    main(args.limit)
