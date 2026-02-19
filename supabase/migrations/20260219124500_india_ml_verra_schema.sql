-- India-first ML + Verra schema updates
-- Keeps migrations idempotent for environments where some tables/columns already exist.

ALTER TABLE public.project_results
ADD COLUMN IF NOT EXISTS land_cover double precision,
ADD COLUMN IF NOT EXISTS ndvi_trend double precision,
ADD COLUMN IF NOT EXISTS ndvi_trend_interpretation text,
ADD COLUMN IF NOT EXISTS fire_burn_percent double precision,
ADD COLUMN IF NOT EXISTS fire_recent_burn boolean,
ADD COLUMN IF NOT EXISTS rainfall_anomaly_percent double precision,
ADD COLUMN IF NOT EXISTS trend_classification text,
ADD COLUMN IF NOT EXISTS ecosystem_type text,
ADD COLUMN IF NOT EXISTS baseline_condition text,
ADD COLUMN IF NOT EXISTS baseline_biomass_carbon double precision,
ADD COLUMN IF NOT EXISTS baseline_soc_total double precision,
ADD COLUMN IF NOT EXISTS baseline_annual_co2 double precision,
ADD COLUMN IF NOT EXISTS baseline_co2_20yr double precision,
ADD COLUMN IF NOT EXISTS baseline_scenario text,
ADD COLUMN IF NOT EXISTS project_annual_co2 double precision,
ADD COLUMN IF NOT EXISTS project_co2_20yr double precision,
ADD COLUMN IF NOT EXISTS additionality_annual_co2 double precision,
ADD COLUMN IF NOT EXISTS additionality_20yr double precision,
ADD COLUMN IF NOT EXISTS pixel_count integer,
ADD COLUMN IF NOT EXISTS ndvi_stddev double precision,
ADD COLUMN IF NOT EXISTS soc_stddev double precision,
ADD COLUMN IF NOT EXISTS rainfall_stddev double precision,
ADD COLUMN IF NOT EXISTS cloud_coverage_percent double precision,
ADD COLUMN IF NOT EXISTS gedi_shot_count integer,
ADD COLUMN IF NOT EXISTS data_confidence_score double precision,
ADD COLUMN IF NOT EXISTS ml_models_used boolean,
ADD COLUMN IF NOT EXISTS biomass_source text,
ADD COLUMN IF NOT EXISTS soc_source text,
ADD COLUMN IF NOT EXISTS model_version_biomass text,
ADD COLUMN IF NOT EXISTS model_version_soc text,
ADD COLUMN IF NOT EXISTS biomass_aboveground double precision,
ADD COLUMN IF NOT EXISTS biomass_belowground double precision,
ADD COLUMN IF NOT EXISTS biomass_total double precision,
ADD COLUMN IF NOT EXISTS prediction_interval_biomass_lower_95 double precision,
ADD COLUMN IF NOT EXISTS prediction_interval_biomass_upper_95 double precision,
ADD COLUMN IF NOT EXISTS prediction_interval_biomass_width double precision,
ADD COLUMN IF NOT EXISTS prediction_interval_soc_lower_95 double precision,
ADD COLUMN IF NOT EXISTS prediction_interval_soc_upper_95 double precision,
ADD COLUMN IF NOT EXISTS prediction_interval_soc_width double precision,
ADD COLUMN IF NOT EXISTS soil_depth_applied text;

CREATE TABLE IF NOT EXISTS public.verra_projects (
  id uuid primary key default gen_random_uuid(),
  verra_id text unique not null,
  name text not null,
  country text,
  status text,
  methodology text default 'VM0047',
  area_ha double precision,
  ecosystem_type text,
  pd_url text,
  mr_urls jsonb,
  geometry jsonb,
  created_at timestamptz default now() not null
);

CREATE INDEX IF NOT EXISTS verra_projects_methodology_idx
  ON public.verra_projects (methodology);

ALTER TABLE public.verra_projects
ADD COLUMN IF NOT EXISTS mr_urls jsonb;

CREATE TABLE IF NOT EXISTS public.verra_monitoring_data (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.verra_projects(id) on delete cascade,
  report_url text,
  monitoring_year integer,
  stocking_index_type text,
  si_biomass_r_squared double precision,
  si_biomass_equation text,
  performance_benchmark double precision,
  carbon_stocks jsonb,
  n_field_plots integer,
  plot_data jsonb,
  gee_features jsonb,
  created_at timestamptz default now() not null
);

CREATE INDEX IF NOT EXISTS verra_monitoring_project_idx
  ON public.verra_monitoring_data (project_id);

ALTER TABLE public.verra_projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.verra_monitoring_data ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'verra_projects'
      AND policyname = 'read_verra_projects'
  ) THEN
    CREATE POLICY "read_verra_projects"
      ON public.verra_projects
      FOR SELECT
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'verra_monitoring_data'
      AND policyname = 'read_verra_monitoring'
  ) THEN
    CREATE POLICY "read_verra_monitoring"
      ON public.verra_monitoring_data
      FOR SELECT
      USING (true);
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'verra_projects'
      AND policyname = 'insert_verra_projects'
  ) THEN
    CREATE POLICY "insert_verra_projects"
      ON public.verra_projects
      FOR INSERT
      WITH CHECK (auth.role() = 'authenticated');
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'verra_monitoring_data'
      AND policyname = 'insert_verra_monitoring'
  ) THEN
    CREATE POLICY "insert_verra_monitoring"
      ON public.verra_monitoring_data
      FOR INSERT
      WITH CHECK (auth.role() = 'authenticated');
  END IF;
END $$;

NOTIFY pgrst, 'reload schema';
