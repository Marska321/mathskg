from typing import Any

from models.domain import MasteryStatus


def compute_mastery_update(
    current_streak: int,
    error_patterns: dict[str, int] | None,
    is_correct: bool,
    error_type: str | None,
) -> dict[str, Any]:
    patterns = dict(error_patterns or {})
    if not isinstance(patterns, dict):
        patterns = {}

    new_streak = current_streak + 1 if is_correct else 0

    if not is_correct and error_type:
        patterns[error_type] = patterns.get(error_type, 0) + 1

    if new_streak >= 3:
        status = MasteryStatus.MASTERED.value
    elif new_streak > 0 or is_correct:
        status = MasteryStatus.LEARNING.value
    else:
        status = MasteryStatus.NEEDS_REVIEW.value

    return {
        "current_streak": new_streak,
        "status": status,
        "error_patterns": patterns,
    }
