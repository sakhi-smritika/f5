import os
from functools import lru_cache
from typing import Any

from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY")
@lru_cache(maxsize=1)
def get_admin_client() -> Any:
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY must be set before running this seed script."
        )
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)