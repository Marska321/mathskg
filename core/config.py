import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


SUPABASE_KEY_ALIASES: tuple[str, ...] = ('SUPABASE_SERVICE_KEY', 'SUPABASE_KEY')
REQUIRED_ENV_VARS: tuple[str, ...] = ('SUPABASE_URL', 'SUPABASE_SERVICE_KEY')

_SETTINGS_CACHE: 'Settings | None' = None
_DOTENV_LOADED = False


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class Settings:
    supabase_url: str
    supabase_service_key: str

    def get_required_env(self, name: str) -> str:
        if name == 'SUPABASE_URL':
            return self.supabase_url
        if name in SUPABASE_KEY_ALIASES:
            return self.supabase_service_key

        value = os.getenv(name)
        if _is_missing(value):
            raise ConfigError(
                f"Missing required environment variable: {name}. "
                'Set it in your environment or .env file before starting the API.'
            )
        return value.strip()


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ''


def _ensure_dotenv_loaded() -> None:
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return

    dotenv_path = Path(__file__).resolve().parent.parent / '.env'
    load_dotenv(dotenv_path=dotenv_path, override=False)
    _DOTENV_LOADED = True


def _get_first_present_env(names: Iterable[str]) -> str | None:
    for name in names:
        value = os.getenv(name)
        if not _is_missing(value):
            return value.strip()
    return None


def _normalize_supabase_key_aliases() -> str:
    service_key = _get_first_present_env(SUPABASE_KEY_ALIASES)
    if _is_missing(service_key):
        raise ConfigError(
            'Missing required environment variable: SUPABASE_SERVICE_KEY. '
            'Set SUPABASE_SERVICE_KEY (preferred) or SUPABASE_KEY in your environment or .env file before starting the API.'
        )

    for name in SUPABASE_KEY_ALIASES:
        os.environ[name] = service_key
    return service_key


def get_settings() -> Settings:
    global _SETTINGS_CACHE
    if _SETTINGS_CACHE is not None:
        return _SETTINGS_CACHE

    _ensure_dotenv_loaded()
    supabase_url = os.getenv('SUPABASE_URL')
    if _is_missing(supabase_url):
        raise ConfigError(
            'Missing required environment variable: SUPABASE_URL. '
            'Set it in your environment or .env file before starting the API.'
        )

    _SETTINGS_CACHE = Settings(
        supabase_url=supabase_url.strip(),
        supabase_service_key=_normalize_supabase_key_aliases(),
    )
    return _SETTINGS_CACHE


def get_required_env(name: str) -> str:
    if name == 'SUPABASE_URL' or name in SUPABASE_KEY_ALIASES:
        return get_settings().get_required_env(name)

    _ensure_dotenv_loaded()
    value = os.getenv(name)
    if _is_missing(value):
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            'Set it in your environment or .env file before starting the API.'
        )
    return value.strip()


def validate_required_env(required: Iterable[str] = REQUIRED_ENV_VARS) -> None:
    settings = get_settings()
    missing: list[str] = []
    for name in required:
        try:
            settings.get_required_env(name)
        except ConfigError:
            missing.append(name)

    if missing:
        names = ', '.join(missing)
        raise ConfigError(
            f"Missing required environment variables: {names}. "
            'Set them in your environment or .env file before starting the API.'
        )


def reset_settings_cache() -> None:
    global _SETTINGS_CACHE, _DOTENV_LOADED
    _SETTINGS_CACHE = None
    _DOTENV_LOADED = False
