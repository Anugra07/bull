ALTER TABLE public.verra_projects
ADD COLUMN IF NOT EXISTS mr_urls jsonb;

NOTIFY pgrst, 'reload config';
