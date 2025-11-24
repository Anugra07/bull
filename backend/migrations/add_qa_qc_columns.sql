-- Migration to add QA/QC Metrics columns to project_results table

ALTER TABLE project_results
ADD COLUMN IF NOT EXISTS pixel_count int4,
ADD COLUMN IF NOT EXISTS ndvi_stddev float8,
ADD COLUMN IF NOT EXISTS soc_stddev float8,
ADD COLUMN IF NOT EXISTS rainfall_stddev float8,
ADD COLUMN IF NOT EXISTS cloud_coverage_percent float8,
ADD COLUMN IF NOT EXISTS gedi_shot_count int4,
ADD COLUMN IF NOT EXISTS data_confidence_score float8;

-- Refresh the schema cache
NOTIFY pgrst, 'reload config';
