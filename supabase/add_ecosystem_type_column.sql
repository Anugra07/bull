-- Migration: Add ecosystem_type column to project_results table
-- Run this in your Supabase SQL Editor

-- Add the ecosystem_type column if it doesn't exist
ALTER TABLE public.project_results 
ADD COLUMN IF NOT EXISTS ecosystem_type text;

-- Optional: Add a comment explaining what this column stores
COMMENT ON COLUMN public.project_results.ecosystem_type IS 'Ecosystem classification: Forest, Cropland, Grassland, Wetland, Shrubland, Plantation, Degraded, Other. Derived from ESA WorldCover land cover classes.';

-- Optional: Add a check constraint to ensure valid values
ALTER TABLE public.project_results
DROP CONSTRAINT IF EXISTS ecosystem_type_check;

ALTER TABLE public.project_results
ADD CONSTRAINT ecosystem_type_check 
CHECK (ecosystem_type IS NULL OR ecosystem_type IN (
    'Forest', 'Cropland', 'Grassland', 'Wetland', 
    'Shrubland', 'Plantation', 'Degraded', 'Other'
));



