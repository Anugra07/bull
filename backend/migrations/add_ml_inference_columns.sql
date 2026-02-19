ALTER TABLE project_results
ADD COLUMN IF NOT EXISTS ml_models_used boolean,
ADD COLUMN IF NOT EXISTS biomass_source text,
ADD COLUMN IF NOT EXISTS soc_source text,
ADD COLUMN IF NOT EXISTS model_version_biomass text,
ADD COLUMN IF NOT EXISTS model_version_soc text,
ADD COLUMN IF NOT EXISTS biomass_aboveground float8,
ADD COLUMN IF NOT EXISTS biomass_belowground float8,
ADD COLUMN IF NOT EXISTS biomass_total float8,
ADD COLUMN IF NOT EXISTS prediction_interval_biomass_lower_95 float8,
ADD COLUMN IF NOT EXISTS prediction_interval_biomass_upper_95 float8,
ADD COLUMN IF NOT EXISTS prediction_interval_biomass_width float8,
ADD COLUMN IF NOT EXISTS prediction_interval_soc_lower_95 float8,
ADD COLUMN IF NOT EXISTS prediction_interval_soc_upper_95 float8,
ADD COLUMN IF NOT EXISTS prediction_interval_soc_width float8,
ADD COLUMN IF NOT EXISTS soil_depth_applied text;

NOTIFY pgrst, 'reload config';
