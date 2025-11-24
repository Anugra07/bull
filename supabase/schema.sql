-- Supabase schema for Phase 1 (Option A)
-- Use auth.users(id) for FK; store geometries as GeoJSON (jsonb) for portability.

-- Extensions (gen_random_uuid)
create extension if not exists pgcrypto;

-- Projects belong to Supabase Auth users
create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null,
  name text not null,
  description text,
  created_at timestamptz default now(),
  constraint projects_user_id_fkey foreign key (user_id) references auth.users(id)
);

-- Polygons associated to a project; geometry stored as GeoJSON
create table if not exists public.project_polygons (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  geometry jsonb not null, -- GeoJSON geometry
  bbox jsonb,              -- [minx, miny, maxx, maxy]
  area_m2 double precision,
  srid integer default 4326,
  created_at timestamptz default now(),
  constraint project_polygons_project_id_fkey foreign key (project_id)
    references public.projects(id) on delete cascade
);

-- Computed results per project (aggregates from GEE + carbon calc)
create table if not exists public.project_results (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null,
  ndvi double precision,
  evi double precision,
  biomass double precision,
  canopy_height double precision,
  soc double precision,
  bulk_density double precision,
  rainfall double precision,
  elevation double precision,
  slope double precision,
  land_cover double precision,
  carbon_biomass double precision,
  soc_total double precision,
  annual_co2 double precision,
  co2_20yr double precision,
  risk_adjusted_co2 double precision,
  created_at timestamptz default now(),
  constraint project_results_project_id_fkey foreign key (project_id)
    references public.projects(id) on delete cascade
);

-- RLS
alter table public.projects enable row level security;
alter table public.project_polygons enable row level security;
alter table public.project_results enable row level security;

-- Projects: owner can select/insert
drop policy if exists "users can read own projects" on public.projects;
create policy "users can read own projects" on public.projects
  for select using (auth.uid() = user_id);
drop policy if exists "users can insert own projects" on public.projects;
create policy "users can insert own projects" on public.projects
  for insert with check (auth.uid() = user_id);

-- Polygons: owner of parent project can select/insert
drop policy if exists "users can read own polygons" on public.project_polygons;
create policy "users can read own polygons" on public.project_polygons
  for select using (
    exists (
      select 1 from public.projects p
      where p.id = project_id and p.user_id = auth.uid()
    )
  );
drop policy if exists "users can insert own polygons" on public.project_polygons;
create policy "users can insert own polygons" on public.project_polygons
  for insert with check (
    exists (
      select 1 from public.projects p
      where p.id = project_id and p.user_id = auth.uid()
    )
  );

-- Results: owner of parent project can select/insert
create policy if not exists "users can read own results" on public.project_results
  for select using (
    exists (
      select 1 from public.projects p
      where p.id = project_id and p.user_id = auth.uid()
    )
  );
create policy if not exists "users can insert own results" on public.project_results
  for insert with check (
    exists (
      select 1 from public.projects p
      where p.id = project_id and p.user_id = auth.uid()
    )
