import os
from functools import lru_cache

from dotenv import load_dotenv
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_PUBLISHABLE_KEY = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
SUPABASE_SECRET_KEY = os.getenv("SUPABASE_SECRET_KEY", "")


@lru_cache
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY environment variables are required"
        )
    return create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)


@lru_cache
def get_supabase_service_client() -> Client:
    """Service-role client for privileged, RLS-bypassing writes (server-side only)."""
    if not SUPABASE_URL or not SUPABASE_SECRET_KEY:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SECRET_KEY environment variables are required"
        )
    return create_client(SUPABASE_URL, SUPABASE_SECRET_KEY)
