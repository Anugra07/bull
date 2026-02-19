# Extract-Only Data Strategy (India-First)

To avoid downloading massive public datasets, the pipeline now uses extraction-first workflows:

1. `backend/scripts/extract_remote_public_data.py`
- Streams remote CSV/TSV in chunks.
- Keeps only required columns (`lat/lon/biomass + selected features`).
- Filters to India bounds by default.
- Writes compact extract files for ingestion.

2. `backend/scripts/ingest_field_data.py`
- Chunked ingestion (`--chunksize`) for large local/remote extracts.
- India-only filtering by default (use `--global` to disable).
- Open/public policy enforcement (`open_public_no_personal_iot`).
- Provenance metadata is written into `field_plots.features.provenance`.

3. `backend/scripts/backfill_field_plot_features.py`
- Backfills missing feature vectors directly from Earth Engine.
- No raster downloads.
- Writes `feature_version=india_v1` and extraction metadata.

## Example

```bash
python backend/scripts/extract_remote_public_data.py \
  --url "https://example.org/huge.csv" \
  --out "data/india_extract.csv" \
  --lat-col latitude --lon-col longitude --biomass-col agb

python backend/scripts/ingest_field_data.py \
  --source gedi-fia \
  --file data/india_extract.csv \
  --chunksize 50000

python backend/scripts/backfill_field_plot_features.py --limit 500
```

## Optimization Notes

- Extraction scripts are column-pruned and chunked to keep memory low.
- Feature extraction is concurrent in `app/services/features.py`.
- Runtime inference uses model feature manifests for deterministic, low-overhead inference.
