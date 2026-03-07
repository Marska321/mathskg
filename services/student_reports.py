from __future__ import annotations

from collections import Counter
from typing import Any

from models.domain import MasteryStatus
from models.students import (
    RepairPathItem,
    StudentMasteryResponse,
    StudentRepairPathResponse,
    StudentReportResponse,
)


def _safe_status(value: str | None) -> str:
    if value is None:
        return MasteryStatus.UNKNOWN.value
    try:
        return MasteryStatus(value).value
    except ValueError:
        return MasteryStatus.UNKNOWN.value


def build_mastery_response(student_id: str, rows: list[dict[str, Any]]) -> StudentMasteryResponse:
    normalized = []
    for row in rows:
        normalized.append(
            {
                "skill_id": row.get("skill_id", ""),
                "status": _safe_status(row.get("status")),
                "current_streak": row.get("current_streak") or 0,
                "error_patterns": row.get("error_patterns") or {},
                "active_repair_path": row.get("active_repair_path") or [],
            }
        )

    counts = Counter(row["status"] for row in normalized)
    summary = {
        MasteryStatus.MASTERED.value: counts.get(MasteryStatus.MASTERED.value, 0),
        MasteryStatus.LEARNING.value: counts.get(MasteryStatus.LEARNING.value, 0),
        MasteryStatus.NEEDS_REVIEW.value: counts.get(MasteryStatus.NEEDS_REVIEW.value, 0),
        MasteryStatus.UNKNOWN.value: counts.get(MasteryStatus.UNKNOWN.value, 0),
    }

    return StudentMasteryResponse(
        student_id=student_id,
        summary=summary,
        skills=sorted(normalized, key=lambda item: item["skill_id"]),
    )


def build_repair_path_response(
    student_id: str,
    rows: list[dict[str, Any]],
    skill_id: str | None = None,
) -> StudentRepairPathResponse:
    items: list[RepairPathItem] = []
    for row in rows:
        source_skill_id = row.get("skill_id", "")
        status = _safe_status(row.get("status"))
        repair_path = row.get("active_repair_path") or []

        if skill_id and source_skill_id != skill_id:
            continue
        if status != MasteryStatus.NEEDS_REVIEW.value:
            continue
        if not repair_path:
            continue

        items.append(RepairPathItem(source_skill_id=source_skill_id, repair_path=repair_path))

    items = sorted(items, key=lambda item: item.source_skill_id)
    return StudentRepairPathResponse(student_id=student_id, items=items)


def build_student_report_response(
    student_id: str,
    mastery_rows: list[dict[str, Any]],
    attempts: list[dict[str, Any]],
) -> StudentReportResponse:
    mastery = build_mastery_response(student_id, mastery_rows)
    repair = build_repair_path_response(student_id, mastery_rows)

    total_attempts = len(attempts)
    correct_attempts = sum(1 for row in attempts if bool(row.get("is_correct")))
    accuracy = round((correct_attempts / total_attempts), 2) if total_attempts else 0.0

    error_counter = Counter(
        row.get("error_type_detected")
        for row in attempts
        if row.get("error_type_detected")
    )
    top_error = error_counter.most_common(1)[0][0] if error_counter else None

    summary = {
        "total_attempts": total_attempts,
        "correct_attempts": correct_attempts,
        "accuracy": accuracy,
        "top_error_type": top_error,
        "skills_tracked": len(mastery.skills),
    }

    return StudentReportResponse(
        student_id=student_id,
        summary=summary,
        mastery_breakdown=mastery.summary,
        recent_repairs=repair.items,
    )
