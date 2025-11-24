-- Migration to add Time-Series and MRV Baseline columns to project_results table

ALTER TABLE project_results
ADD COLUMN IF NOT EXISTS ndvi_trend float8,
ADD COLUMN IF NOT EXISTS ndvi_trend_interpretation text,
ADD COLUMN IF NOT EXISTS fire_burn_percent float8,
ADD COLUMN IF NOT EXISTS fire_recent_burn boolean,
ADD COLUMN IF NOT EXISTS rainfall_anomaly_percent float8,
ADD COLUMN IF NOT EXISTS trend_classification text,
ADD COLUMN IF NOT EXISTS ecosystem_type text,
ADD COLUMN IF NOT EXISTS baseline_condition text,
ADD COLUMN IF NOT EXISTS baseline_biomass_carbon float8,
ADD COLUMN IF NOT EXISTS baseline_soc_total float8,
ADD COLUMN IF NOT EXISTS baseline_annual_co2 float8,
ADD COLUMN IF NOT EXISTS baseline_co2_20yr float8,
ADD COLUMN IF NOT EXISTS baseline_scenario text,
ADD COLUMN IF NOT EXISTS project_annual_co2 float8,
ADD COLUMN IF NOT EXISTS project_co2_20yr float8,
ADD COLUMN IF NOT EXISTS additionality_annual_co2 float8,
ADD COLUMN IF NOT EXISTS additionality_20yr float8;

-- Refresh the schema cache (Supabase sometimes needs this)
NOTIFY pgrst, 'reload config';
