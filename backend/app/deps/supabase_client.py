import os
from typing import Any

_supabase: Any | None = None

def get_supabase() -> Any:
    global _supabase
    if _supabase is None:
        try:
            from supabase import create_client
        except Exception as e:
            raise RuntimeError(f"supabase client library not available: {e}")

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        if not url or not key:
            raise RuntimeError("Supabase env vars missing: SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY/ANON_KEY")
        _supabase = create_client(url, key)
    return _supabase
