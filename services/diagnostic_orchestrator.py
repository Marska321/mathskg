from __future__ import annotations

from typing import Callable, Iterable

from models.diagnostic_bank import DiagnosticAnchorQuestion
from models.domain import MasteryStatus
from services.diagnostic_engine import DiagnosticGraph


MAX_QUESTIONS = 25


AnchorFetcher = Callable[[str], DiagnosticAnchorQuestion | None]


def build_starting_skill_queue(graph: DiagnosticGraph, current_state: dict[str, str]) -> list[str]:
    queue: list[str] = []
    seen_domains: set[str] = set()

    for skill_id in graph.get_starting_nodes():
        if current_state.get(skill_id) != MasteryStatus.UNKNOWN.value:
            continue

        domain = graph.get_skill_domain(skill_id)
        if domain in seen_domains:
            continue

        seen_domains.add(domain)
        queue.append(skill_id)

    if queue:
        return queue

    return [
        skill_id
        for skill_id in graph.get_sorted_skill_ids()
        if current_state.get(skill_id) == MasteryStatus.UNKNOWN.value
    ]


def extend_skill_queue(
    pending_skill_ids: Iterable[str],
    candidate_skill_ids: Iterable[str],
    current_state: dict[str, str],
    asked_skill_ids: Iterable[str],
) -> list[str]:
    asked = set(asked_skill_ids)
    merged: list[str] = []

    for skill_id in [*pending_skill_ids, *candidate_skill_ids]:
        if current_state.get(skill_id) != MasteryStatus.UNKNOWN.value:
            continue
        if skill_id in asked or skill_id in merged:
            continue
        merged.append(skill_id)

    return merged


def select_next_anchor_question(
    graph: DiagnosticGraph,
    current_state: dict[str, str],
    pending_skill_ids: Iterable[str],
    asked_skill_ids: Iterable[str],
    fetch_anchor: AnchorFetcher,
) -> tuple[str | None, DiagnosticAnchorQuestion | None, list[str]]:
    queue = extend_skill_queue(pending_skill_ids, [], current_state, asked_skill_ids)
    asked = set(asked_skill_ids)

    next_skill_id, anchor, remaining_queue = _drain_queue_for_anchor(queue, fetch_anchor)
    if anchor is not None:
        return next_skill_id, anchor, remaining_queue

    fallback_candidates = [
        skill_id
        for skill_id in graph.get_sorted_skill_ids()
        if current_state.get(skill_id) == MasteryStatus.UNKNOWN.value and skill_id not in asked
    ]
    fallback_queue = extend_skill_queue(remaining_queue, fallback_candidates, current_state, asked)
    next_skill_id, anchor, remaining_queue = _drain_queue_for_anchor(fallback_queue, fetch_anchor)
    return next_skill_id, anchor, remaining_queue


def should_complete_diagnostic(
    current_state: dict[str, str],
    question_count: int,
    max_questions: int = MAX_QUESTIONS,
) -> bool:
    if question_count >= max_questions:
        return True

    return not any(state == MasteryStatus.UNKNOWN.value for state in current_state.values())


def _drain_queue_for_anchor(
    queue: list[str],
    fetch_anchor: AnchorFetcher,
) -> tuple[str | None, DiagnosticAnchorQuestion | None, list[str]]:
    remaining_queue = list(queue)

    while remaining_queue:
        skill_id = remaining_queue.pop(0)
        anchor = fetch_anchor(skill_id)
        if anchor is not None:
            return skill_id, anchor, remaining_queue

    return None, None, remaining_queue
