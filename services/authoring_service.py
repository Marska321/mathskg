from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


class AuthoringError(ValueError):
    """Raised for invalid authoring workflow actions."""


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_skill_create_payload(payload: dict[str, Any]) -> dict[str, Any]:
    data = dict(payload)
    if not data.get("approval_status"):
        data["approval_status"] = "pending"
    return data


def normalize_skill_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def validate_publish_transition(current_status: str | None, force: bool = False) -> None:
    normalized = (current_status or "pending").strip().lower()
    allowed = {"pending", "draft", "review", "live"}

    if normalized not in allowed:
        raise AuthoringError(f"Invalid approval_status '{current_status}' for publish transition.")

    if normalized == "live" and not force:
        raise AuthoringError("Skill is already live. Use force=true to republish.")


def ensure_template_exists(template_rows: list[dict[str, Any]], force: bool = False) -> None:
    if template_rows:
        return
    if force:
        return
    raise AuthoringError(
        "No templates found for this skill. Create at least one template before publishing, or use force=true."
    )


def build_publish_update(skill_id: str) -> dict[str, Any]:
    return {
        "skill_id": skill_id,
        "approval_status": "live",
        "published_at": _utc_now_iso(),
    }
