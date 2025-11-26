-- Migration: Add land_cover column to project_results table
-- Run this in your Supabase SQL Editor if the column doesn't exist

-- Add the land_cover column if it doesn't exist
ALTER TABLE public.project_results 
ADD COLUMN IF NOT EXISTS land_cover double precision;

-- Optional: Add a comment explaining what this column stores
COMMENT ON COLUMN public.project_results.land_cover IS 'ESA WorldCover class code (10=Trees, 20=Shrubland, 30=Grassland, 40=Cropland, 50=Urban, 60=Bare, 70=Snow/Ice, 80=Water, 90=Herbaceous, 95=Mangroves, 100=Moss)';



