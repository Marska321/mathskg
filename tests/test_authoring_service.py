from services.authoring_service import (
    AuthoringError,
    build_publish_update,
    ensure_template_exists,
    normalize_skill_create_payload,
    normalize_skill_update_payload,
    validate_publish_transition,
)


def test_normalize_skill_create_payload_sets_default_status():
    payload = {"skill_id": "A", "skill_name": "Skill A", "approval_status": ""}
    normalized = normalize_skill_create_payload(payload)
    assert normalized["approval_status"] == "pending"


def test_normalize_skill_update_payload_drops_none_fields():
    payload = {"skill_name": "Updated", "difficulty": None, "approval_status": "review"}
    normalized = normalize_skill_update_payload(payload)
    assert normalized == {"skill_name": "Updated", "approval_status": "review"}


def test_validate_publish_transition_rejects_live_without_force():
    try:
        validate_publish_transition("live", force=False)
        assert False, "Expected AuthoringError"
    except AuthoringError:
        assert True


def test_validate_publish_transition_accepts_live_with_force():
    validate_publish_transition("live", force=True)


def test_ensure_template_exists_requires_template_unless_forced():
    try:
        ensure_template_exists([], force=False)
        assert False, "Expected AuthoringError"
    except AuthoringError:
        assert True

    ensure_template_exists([], force=True)


def test_build_publish_update_sets_live_status_and_timestamp():
    payload = build_publish_update("A")
    assert payload["skill_id"] == "A"
    assert payload["approval_status"] == "live"
    assert isinstance(payload["published_at"], str)
    assert "T" in payload["published_at"]
