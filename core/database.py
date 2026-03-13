from typing import Any

from supabase import Client, create_client

from core.config import get_settings


_SUPABASE_CACHE: Client | None = None


def get_supabase() -> Client:
    global _SUPABASE_CACHE
    if _SUPABASE_CACHE is None:
        settings = get_settings()
        _SUPABASE_CACHE = create_client(
            settings.supabase_url,
            settings.supabase_service_key,
        )
    return _SUPABASE_CACHE


def reset_supabase_cache() -> None:
    global _SUPABASE_CACHE
    _SUPABASE_CACHE = None


class _SupabaseProxy:
    def __getattr__(self, name: str) -> Any:
        return getattr(get_supabase(), name)

    def __repr__(self) -> str:
        return '<LazySupabaseProxy>'


supabase = _SupabaseProxy()
