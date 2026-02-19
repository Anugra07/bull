-- Verra Project Metadata
create table public.verra_projects (
  id uuid primary key default gen_random_uuid(),
  verra_id text unique not null,         -- e.g. 'VCS-2847'
  name text not null,
  country text,
  status text,                           -- 'Registered', 'Under Validation', etc.
  methodology text default 'VM0047',
  area_ha float,
  ecosystem_type text,                   -- inferred from description
  pd_url text,                           -- Project Description PDF URL
  mr_urls jsonb,                         -- Monitoring Report PDF URLs
  geometry jsonb,                        -- GeoJSON (if extractable from PD)
  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index verra_projects_methodology_idx on public.verra_projects (methodology);

-- Verra Monitoring Report Extracted Data
create table public.verra_monitoring_data (
  id uuid primary key default gen_random_uuid(),
  project_id uuid references public.verra_projects(id) on delete cascade,
  report_url text,
  monitoring_year int,

  -- VM0047-specific extractions
  stocking_index_type text,              -- 'NDVI', 'NDFI', 'EVI', 'GEDI', 'LiDAR'
  si_biomass_r_squared float,            -- R² of SI→Biomass regression
  si_biomass_equation text,              -- e.g. 'AGB = 234.5 * NDVI - 12.3'
  performance_benchmark float,
  carbon_stocks jsonb,                   -- {"t0": 45.2, "t5": 78.1, ...} tC/ha
  n_field_plots int,
  plot_data jsonb,                       -- [{biomass: 120, dbh: 15, species: "Teak"}, ...]

  -- GEE features for this project area + year
  gee_features jsonb,

  created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

create index verra_monitoring_project_idx on public.verra_monitoring_data (project_id);

-- RLS
alter table public.verra_projects enable row level security;
alter table public.verra_monitoring_data enable row level security;

create policy "read_verra_projects" on public.verra_projects for select using (true);
create policy "read_verra_monitoring" on public.verra_monitoring_data for select using (true);
create policy "insert_verra_projects" on public.verra_projects for insert with check (auth.role() = 'authenticated');
create policy "insert_verra_monitoring" on public.verra_monitoring_data for insert with check (auth.role() = 'authenticated');
