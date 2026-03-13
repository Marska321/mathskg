from __future__ import annotations

from typing import Any, Callable

from models.diagnostic_bank import DiagnosticAnchorQuestion
from models.domain import MasteryStatus
from services.graph_service import get_skill_prerequisites


PrerequisiteLookup = Callable[[str], list[str]]


def build_diagnostic_item_payload(
    diagnostic_session_id: str,
    student_id: str,
    question_order: int,
    anchor: DiagnosticAnchorQuestion | dict[str, Any],
    student_answer: Any,
    is_correct: bool,
) -> dict[str, Any]:
    anchor_record = anchor if isinstance(anchor, DiagnosticAnchorQuestion) else DiagnosticAnchorQuestion.model_validate(anchor)
    return {
        'diagnostic_session_id': diagnostic_session_id,
        'student_id': student_id,
        'question_id': anchor_record.question_id,
        'skill_id': anchor_record.skill_id,
        'domain': anchor_record.domain,
        'cluster': anchor_record.cluster,
        'question_text': anchor_record.question_text,
        'question_order': question_order,
        'student_answer': student_answer,
        'is_correct': is_correct,
    }


def persist_diagnostic_item(
    repository,
    diagnostic_session_id: str,
    student_id: str,
    question_order: int,
    anchor: DiagnosticAnchorQuestion | dict[str, Any],
    student_answer: Any,
    is_correct: bool,
) -> dict[str, Any]:
    payload = build_diagnostic_item_payload(
        diagnostic_session_id,
        student_id,
        question_order,
        anchor,
        student_answer,
        is_correct,
    )
    repository.table('diagnostic_items').insert(payload).execute()
    return payload


def build_skill_estimate_payloads(
    diagnostic_session_id: str,
    student_id: str,
    current_state: dict[str, str],
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []

    for skill_id, state in sorted(current_state.items()):
        mapped = _map_state_to_estimate(state)
        if mapped is None:
            continue
        payloads.append(
            {
                'diagnostic_session_id': diagnostic_session_id,
                'student_id': student_id,
                'skill_id': skill_id,
                'diagnostic_state': state,
                'estimated_mastery_probability': mapped['estimated_mastery_probability'],
                'mastery_status': mapped['mastery_status'],
                'student_mastery_status': mapped['student_mastery_status'],
                'confidence_level': mapped['confidence_level'],
                'source': mapped['source'],
            }
        )

    return payloads


def build_student_mastery_from_estimates(
    payloads: list[dict[str, Any]],
    prerequisite_lookup: PrerequisiteLookup = get_skill_prerequisites,
) -> list[dict[str, Any]]:
    mastery_payloads: list[dict[str, Any]] = []
    for payload in payloads:
        active_repair_path = []
        if payload['student_mastery_status'] == MasteryStatus.NEEDS_REVIEW.value:
            active_repair_path = prerequisite_lookup(payload['skill_id'])

        mastery_payloads.append(
            {
                'student_id': payload['student_id'],
                'skill_id': payload['skill_id'],
                'status': payload['student_mastery_status'],
                'active_repair_path': active_repair_path,
            }
        )
    return mastery_payloads


def persist_skill_estimates(
    repository,
    diagnostic_session_id: str,
    student_id: str,
    current_state: dict[str, str],
    prerequisite_lookup: PrerequisiteLookup = get_skill_prerequisites,
) -> list[dict[str, Any]]:
    payloads = build_skill_estimate_payloads(diagnostic_session_id, student_id, current_state)
    if not payloads:
        return []

    repository.table('diagnostic_skill_estimates').upsert(
        payloads,
        on_conflict='diagnostic_session_id,skill_id',
    ).execute()

    mastery_payloads = build_student_mastery_from_estimates(
        payloads,
        prerequisite_lookup=prerequisite_lookup,
    )
    repository.table('student_mastery').upsert(
        mastery_payloads,
        on_conflict='student_id,skill_id',
    ).execute()
    return payloads


def _map_state_to_estimate(state: str) -> dict[str, Any] | None:
    if state == MasteryStatus.MASTERED.value:
        return {
            'estimated_mastery_probability': 1.0,
            'mastery_status': 'mastered',
            'student_mastery_status': MasteryStatus.MASTERED.value,
            'confidence_level': 'high',
            'source': 'direct',
        }

    if state == MasteryStatus.ASSUMED_MASTERED.value:
        return {
            'estimated_mastery_probability': 0.85,
            'mastery_status': 'mastered',
            'student_mastery_status': MasteryStatus.MASTERED.value,
            'confidence_level': 'medium',
            'source': 'propagated',
        }

    if state in {MasteryStatus.GAP.value, MasteryStatus.ASSUMED_GAP.value, MasteryStatus.NEEDS_REVIEW.value}:
        return {
            'estimated_mastery_probability': 0.2 if state == MasteryStatus.GAP.value else 0.35,
            'mastery_status': 'remediation',
            'student_mastery_status': MasteryStatus.NEEDS_REVIEW.value,
            'confidence_level': 'high' if state == MasteryStatus.GAP.value else 'medium',
            'source': 'direct' if state == MasteryStatus.GAP.value else 'propagated',
        }

    if state == MasteryStatus.LEARNING.value:
        return {
            'estimated_mastery_probability': 0.6,
            'mastery_status': 'learning',
            'student_mastery_status': MasteryStatus.LEARNING.value,
            'confidence_level': 'medium',
            'source': 'direct',
        }

    return None
