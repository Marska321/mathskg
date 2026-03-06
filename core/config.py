import os
from typing import Iterable


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


REQUIRED_ENV_VARS: tuple[str, ...] = ("SUPABASE_URL", "SUPABASE_KEY")


def _is_missing(value: str | None) -> bool:
    return value is None or value.strip() == ""


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if _is_missing(value):
        raise ConfigError(
            f"Missing required environment variable: {name}. "
            "Set it in your environment or .env file before starting the API."
        )
    return value


def validate_required_env(required: Iterable[str] = REQUIRED_ENV_VARS) -> None:
    missing = [name for name in required if _is_missing(os.getenv(name))]
    if missing:
        names = ", ".join(missing)
        raise ConfigError(
            f"Missing required environment variables: {names}. "
            "Set them in your environment or .env file before starting the API."
        )
