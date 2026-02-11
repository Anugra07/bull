-- Create table for storing field plot data (Ground Truth)
create table public.field_plots (
  id uuid primary key default gen_random_uuid(),
  dataset_name text not null, -- e.g. 'GEDI-FIA', 'BioMassters'
  measurement_date date,
  latitude float not null,
  longitude float not null,
  
  -- Biomass & Carbon Data
  biomass_agb float, -- Above-Ground Biomass (t/ha)
  biomass_bgb float, -- Below-Ground Biomass (t/ha)
  soc_0_30cm float, -- Soil Organic Carbon 0-30cm (tC/ha)
  
  -- Metadata
  ecosystem_type text, -- e.g. 'Forest', 'Grassland'
  climate_zone text, -- e.g. 'Tropical', 'Temperate'
  
  -- ML Features (stored as JSONB for flexibility)
  features jsonb, -- GEE-extracted features ( NDVI, GEDI_L4A, Rainfall, etc.)
  
  -- Metadata
  created_at timestamp with time zone default timezone('utc'::text, now()) not null,
  updated_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Spatially index the coordinates for fast querying
create index field_plots_geo_idx on public.field_plots using gist (
  st_setsrid(st_makepoint(longitude, latitude), 4326)
);

-- RLS Policies (Enable Read Access for Authenticated Users)
alter table public.field_plots enable row level security;

create policy "Enable read access for all users"
on public.field_plots
for select using (true);

create policy "Enable insert for authenticated users only"
on public.field_plots
for insert with check (auth.role() = 'authenticated');
