import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from core.database import supabase


_TABLE_NAME = 'diagnostic_sessions'
_USE_MEMORY_ONLY = False
_MEMORY_SESSIONS: dict[str, dict[str, Any]] = {}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_payload(session: dict[str, Any]) -> dict[str, Any]:
    return {
        'session_id': session['session_id'],
        'student_id': session['student_id'],
        'status': session['status'],
        'current_state': session['current_state'],
        'question_count': session['question_count'],
        'asked_skills': session['asked_skills'],
        'pending_skill_ids': session.get('pending_skill_ids', []),
        'next_skill_id': session.get('next_skill_id'),
        'placement_skill_id': session.get('placement_skill_id'),
        'confidence': session.get('confidence'),
        'created_at': session['created_at'],
        'updated_at': session['updated_at'],
    }


def _persist_to_db(payload: dict[str, Any]) -> bool:
    global _USE_MEMORY_ONLY
    if _USE_MEMORY_ONLY:
        return False

    try:
        supabase.table(_TABLE_NAME).upsert(payload, on_conflict='session_id').execute()
        return True
    except Exception:
        _USE_MEMORY_ONLY = True
        return False


def _fetch_from_db(session_id: str) -> dict[str, Any] | None:
    global _USE_MEMORY_ONLY
    if _USE_MEMORY_ONLY:
        return None

    try:
        response = (
            supabase.table(_TABLE_NAME)
            .select('*')
            .eq('session_id', session_id)
            .limit(1)
            .execute()
        )
        if not response.data:
            return None
        return response.data[0]
    except Exception:
        _USE_MEMORY_ONLY = True
        return None


def create_diagnostic_session(
    student_id: str,
    current_state: dict[str, str],
    pending_skill_ids: list[str] | None = None,
) -> dict[str, Any]:
    now = _utc_now()
    session = {
        'session_id': str(uuid.uuid4()),
        'student_id': student_id,
        'status': 'in_progress',
        'current_state': copy.deepcopy(current_state),
        'question_count': 0,
        'asked_skills': [],
        'pending_skill_ids': copy.deepcopy(pending_skill_ids or []),
        'next_skill_id': None,
        'placement_skill_id': None,
        'confidence': None,
        'created_at': now,
        'updated_at': now,
    }

    payload = _to_payload(session)
    persisted = _persist_to_db(payload)
    if not persisted:
        _MEMORY_SESSIONS[session['session_id']] = copy.deepcopy(session)

    return session


def get_diagnostic_session(session_id: str) -> dict[str, Any] | None:
    db_session = _fetch_from_db(session_id)
    if db_session is not None:
        return db_session

    session = _MEMORY_SESSIONS.get(session_id)
    return copy.deepcopy(session) if session else None


def update_diagnostic_session(session_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
    existing = get_diagnostic_session(session_id)
    if existing is None:
        return None

    existing.update(copy.deepcopy(updates))
    existing['updated_at'] = _utc_now()

    payload = _to_payload(existing)
    persisted = _persist_to_db(payload)
    if not persisted:
        _MEMORY_SESSIONS[session_id] = copy.deepcopy(existing)

    return copy.deepcopy(existing)
