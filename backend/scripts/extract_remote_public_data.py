"""
Extract-only pipeline for very large public datasets.

This script reads remote CSV/TSV data in streaming chunks, selects only required
columns, optionally filters to India bounds, and writes a compact local extract.

Example:
  python backend/scripts/extract_remote_public_data.py \
    --url https://example.com/huge.csv \
    --out data/extract_india.csv \
    --lat-col latitude --lon-col longitude --biomass-col agb
"""

import argparse
import os
from typing import List

import pandas as pd


INDIA_BOUNDS = {
    "lat_min": 6.0,
    "lat_max": 38.5,
    "lon_min": 68.0,
    "lon_max": 98.0,
}


def in_india(lat: float, lon: float) -> bool:
    return (
        INDIA_BOUNDS["lat_min"] <= lat <= INDIA_BOUNDS["lat_max"]
        and INDIA_BOUNDS["lon_min"] <= lon <= INDIA_BOUNDS["lon_max"]
    )


def parse_columns(value: str) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Stream extract from large remote CSV/TSV datasets")
    parser.add_argument("--url", required=True, help="Remote CSV/TSV URL")
    parser.add_argument("--out", required=True, help="Output CSV path")
    parser.add_argument("--chunksize", type=int, default=100000, help="Streaming chunk size")
    parser.add_argument("--sep", default=",", help="Delimiter (default ,)")
    parser.add_argument("--columns", default="", help="Comma-separated extra columns to keep")
    parser.add_argument("--lat-col", default="latitude", help="Latitude column name")
    parser.add_argument("--lon-col", default="longitude", help="Longitude column name")
    parser.add_argument("--biomass-col", default="agb", help="Biomass column name")
    parser.add_argument("--global", dest="india_only", action="store_false", help="Disable India-only filtering")
    parser.add_argument("--max-rows", type=int, default=0, help="Stop after N accepted rows (0 = all)")
    parser.set_defaults(india_only=True)
    args = parser.parse_args()

    keep_cols = set(parse_columns(args.columns))
    keep_cols.update([args.lat_col, args.lon_col, args.biomass_col])

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)

    written = 0
    scanned = 0
    first_write = True

    reader = pd.read_csv(
        args.url,
        sep=args.sep,
        chunksize=args.chunksize,
        usecols=lambda c: c in keep_cols,
        low_memory=False,
    )

    for chunk in reader:
        scanned += len(chunk)

        # Normalize required column names to standard output shape.
        chunk = chunk.rename(
            columns={
                args.lat_col: "latitude",
                args.lon_col: "longitude",
                args.biomass_col: "biomass_agb",
            }
        )

        chunk = chunk.dropna(subset=["latitude", "longitude", "biomass_agb"])
        chunk["latitude"] = pd.to_numeric(chunk["latitude"], errors="coerce")
        chunk["longitude"] = pd.to_numeric(chunk["longitude"], errors="coerce")
        chunk["biomass_agb"] = pd.to_numeric(chunk["biomass_agb"], errors="coerce")
        chunk = chunk.dropna(subset=["latitude", "longitude", "biomass_agb"])

        if args.india_only:
            chunk = chunk[
                chunk.apply(lambda r: in_india(float(r["latitude"]), float(r["longitude"])), axis=1)
            ]

        if len(chunk) == 0:
            continue

        if args.max_rows > 0 and written + len(chunk) > args.max_rows:
            chunk = chunk.iloc[: max(0, args.max_rows - written)]

        chunk.to_csv(args.out, mode="w" if first_write else "a", index=False, header=first_write)
        first_write = False
        written += len(chunk)

        print(f"scanned={scanned} accepted={written}")

        if args.max_rows > 0 and written >= args.max_rows:
            break

    print(f"Extraction complete. output={args.out} scanned={scanned} accepted={written}")


if __name__ == "__main__":
    main()
