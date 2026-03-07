from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from models.domain import MasteryStatus
from models.teacher import (
    TeacherBottlenecksResponse,
    TeacherCapsCoverageResponse,
    TeacherHeatmapResponse,
)


def _safe_status(value: str | None) -> str:
    if value is None:
        return MasteryStatus.UNKNOWN.value
    try:
        return MasteryStatus(value).value
    except ValueError:
        return MasteryStatus.UNKNOWN.value


def _extract_caps_topic(caps_reference: Any) -> str:
    if isinstance(caps_reference, dict):
        topic = caps_reference.get("topic")
        if isinstance(topic, str) and topic.strip():
            return topic.strip()
    if isinstance(caps_reference, str) and caps_reference.strip():
        return caps_reference.strip()
    return "Unmapped"


def build_teacher_heatmap_response(
    class_id: str,
    student_ids: list[str],
    mastery_rows: list[dict[str, Any]],
) -> TeacherHeatmapResponse:
    by_skill = defaultdict(lambda: Counter())

    for row in mastery_rows:
        skill_id = row.get("skill_id", "")
        if not skill_id:
            continue
        status = _safe_status(row.get("status"))
        by_skill[skill_id][status] += 1

    learners = len(student_ids)
    skills = []
    for skill_id in sorted(by_skill.keys()):
        counts = by_skill[skill_id]
        mastered = counts.get(MasteryStatus.MASTERED.value, 0)
        learning = counts.get(MasteryStatus.LEARNING.value, 0)
        needs_review = counts.get(MasteryStatus.NEEDS_REVIEW.value, 0)
        unknown = max(learners - (mastered + learning + needs_review), 0)
        percent_mastered = round((mastered / learners) * 100, 2) if learners else 0.0

        skills.append(
            {
                "skill_id": skill_id,
                "mastered": mastered,
                "learning": learning,
                "needs_review": needs_review,
                "unknown": unknown,
                "percent_mastered": percent_mastered,
            }
        )

    return TeacherHeatmapResponse(class_id=class_id, learners=learners, skills=skills)


def build_teacher_bottlenecks_response(
    class_id: str,
    student_ids: list[str],
    attempt_rows: list[dict[str, Any]],
    min_attempts: int = 2,
) -> TeacherBottlenecksResponse:
    attempts_by_skill: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in attempt_rows:
        skill_id = row.get("skill_id", "")
        if skill_id:
            attempts_by_skill[skill_id].append(row)

    bottlenecks = []
    for skill_id in sorted(attempts_by_skill.keys()):
        attempts = attempts_by_skill[skill_id]
        total = len(attempts)
        if total < min_attempts:
            continue

        failures = [row for row in attempts if not bool(row.get("is_correct"))]
        failure_count = len(failures)
        failure_rate = round((failure_count / total), 2)

        if failure_count == 0:
            continue

        error_counter = Counter(
            row.get("error_type_detected")
            for row in failures
            if row.get("error_type_detected")
        )
        top_error = error_counter.most_common(1)[0][0] if error_counter else None

        bottlenecks.append(
            {
                "skill_id": skill_id,
                "attempts": total,
                "failures": failure_count,
                "failure_rate": failure_rate,
                "top_error_type": top_error,
            }
        )

    bottlenecks.sort(key=lambda row: (-row["failure_rate"], -row["failures"], row["skill_id"]))
    return TeacherBottlenecksResponse(
        class_id=class_id,
        learners=len(student_ids),
        bottlenecks=bottlenecks,
    )


def build_teacher_caps_coverage_response(
    class_id: str,
    student_ids: list[str],
    mastery_rows: list[dict[str, Any]],
    skills_rows: list[dict[str, Any]],
) -> TeacherCapsCoverageResponse:
    topic_by_skill: dict[str, str] = {}
    skills_per_topic: Counter[str] = Counter()

    for row in skills_rows:
        skill_id = row.get("skill_id", "")
        if not skill_id:
            continue
        topic = _extract_caps_topic(row.get("caps_reference"))
        topic_by_skill[skill_id] = topic
        skills_per_topic[topic] += 1

    mastered_by_topic: Counter[str] = Counter()
    mastered_skills = {
        row.get("skill_id")
        for row in mastery_rows
        if _safe_status(row.get("status")) == MasteryStatus.MASTERED.value
    }

    for skill_id in mastered_skills:
        topic = topic_by_skill.get(skill_id, "Unmapped")
        mastered_by_topic[topic] += 1

    coverage_rows = []
    for topic in sorted(skills_per_topic.keys()):
        total = skills_per_topic[topic]
        mastered = mastered_by_topic.get(topic, 0)
        coverage = round((mastered / total) * 100, 2) if total else 0.0
        coverage_rows.append(
            {
                "topic": topic,
                "skills_total": total,
                "skills_mastered_by_class": mastered,
                "coverage_percent": coverage,
            }
        )

    total_skills = sum(skills_per_topic.values())
    total_mastered = sum(mastered_by_topic.values())
    overall_coverage = round((total_mastered / total_skills) * 100, 2) if total_skills else 0.0

    summary = {
        "topics": len(skills_per_topic),
        "skills_total": total_skills,
        "skills_mastered_by_class": total_mastered,
        "overall_coverage_percent": overall_coverage,
    }

    return TeacherCapsCoverageResponse(
        class_id=class_id,
        learners=len(student_ids),
        summary=summary,
        coverage=coverage_rows,
    )
