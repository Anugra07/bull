# Carbon Offset Land Analyzer – Monorepo (Phase 1 MVP)

This monorepo contains:

- frontend/ — Next.js 14 (App Router), React, Leaflet, TailwindCSS
- backend/ — FastAPI (Python), Geospatial + Earth Engine integrations
- supabase/ — SQL schema for tables

## Tech Stack

Frontend: Next.js 14, React, Leaflet.js, OpenStreetMap tiles, TailwindCSS
Backend: FastAPI (Python), earthengine-api, geopandas, rasterio, shapely, numpy, scikit-image, reportlab
Auth/DB: Supabase Auth, Supabase Postgres

## Getting Started

1) Copy envs

- Root
  - cp .env.example .env
- Frontend
  - cd frontend && cp .env.local.example .env.local
- Backend
  - cd backend && cp .env.example .env

2) Install & run

- Frontend
  - pnpm i (or npm i / yarn)
  - pnpm dev
- Backend
  - python -m venv .venv && source .venv/bin/activate
  - pip install -r requirements.txt
  - uvicorn app.main:app --reload --port 8000

## Supabase

- Create a Supabase project (free tier)
- Set the variables from your project into .env files
- Apply schema from supabase/schema.sql

## Structure

```
frontend/
  app/
  src/
  styles/
backend/
  app/
  requirements.txt
supabase/
  schema.sql
```

## Phase 1 Tasks

- Task 1: Project setup (this commit)
- Task 2: Frontend UI pages + auth wiring
- Task 3: Polygon validation + storage
- Task 4: Earth Engine integrations
- Task 5: Carbon computations
- Task 6: Dashboard visuals
- Task 7: PDF report

## License
MIT
