import os
from typing import Iterable

from dotenv import load_dotenv

# Force Python to load the .env file immediately before doing anything else.
load_dotenv()

SUPABASE_KEY_ALIASES: tuple[str, ...] = ('SUPABASE_SERVICE_KEY', 'SUPABASE_KEY')
REQUIRED_ENV_VARS: tuple[str, ...] = ('SUPABASE_URL', 'SUPABASE_SERVICE_KEY')


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ''


def _get_first_present_env(names: Iterable[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if not _is_missing(value):
            return value
    return None


def _sync_supabase_key_aliases() -> None:
    key_value = _get_first_present_env(SUPABASE_KEY_ALIASES)
    if _is_missing(key_value):
        return

    for name in SUPABASE_KEY_ALIASES:
        os.environ.setdefault(name, key_value)


_sync_supabase_key_aliases()


def get_required_env(name: str) -> str:
    if name in SUPABASE_KEY_ALIASES:
        _sync_supabase_key_aliases()
        value = _get_first_present_env(SUPABASE_KEY_ALIASES)
    else:
        value = os.getenv(name)

    if _is_missing(value):
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            'Set it in your environment or .env file before starting the API.'
        )
    return value


def validate_required_env(required: Iterable[str] = REQUIRED_ENV_VARS) -> None:
    _sync_supabase_key_aliases()
    missing: list[str] = []
    for name in required:
        if name in SUPABASE_KEY_ALIASES:
            if _is_missing(_get_first_present_env(SUPABASE_KEY_ALIASES)):
                missing.append(name)
            continue
        if _is_missing(os.getenv(name)):
            missing.append(name)

    if missing:
        names = ', '.join(missing)
        raise ConfigError(
            f"Missing required environment variables: {names}. "
            'Set them in your environment or .env file before starting the API.'
        )
