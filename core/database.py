from supabase import Client, create_client

from core.config import get_required_env


supabase: Client = create_client(
    get_required_env("SUPABASE_URL"),
    get_required_env("SUPABASE_KEY"),
)
