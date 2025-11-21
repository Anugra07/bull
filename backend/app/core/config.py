from pydantic import BaseModel
import os

class Settings(BaseModel):
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_anon_key: str = os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")

    gee_service_account: str = os.getenv("GEE_SERVICE_ACCOUNT", "")
    gee_private_key: str = os.getenv("GEE_PRIVATE_KEY", "")

settings = Settings()
