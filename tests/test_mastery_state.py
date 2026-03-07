from models.domain import MasteryStatus
from services.mastery_state import compute_mastery_update


def test_compute_mastery_update_increments_streak_on_correct_answer():
    result = compute_mastery_update(
        current_streak=1,
        error_patterns={"UNKNOWN_ERROR": 2},
        is_correct=True,
        error_type=None,
    )

    assert result["current_streak"] == 2
    assert result["status"] == MasteryStatus.LEARNING.value
    assert result["error_patterns"] == {"UNKNOWN_ERROR": 2}


def test_compute_mastery_update_marks_mastered_at_three_streak():
    result = compute_mastery_update(
        current_streak=2,
        error_patterns={},
        is_correct=True,
        error_type=None,
    )

    assert result["current_streak"] == 3
    assert result["status"] == MasteryStatus.MASTERED.value


def test_compute_mastery_update_resets_streak_and_sets_needs_review_on_failure():
    result = compute_mastery_update(
        current_streak=2,
        error_patterns={"MC_SUB_01_ADDED_INSTEAD": 1},
        is_correct=False,
        error_type="MC_SUB_01_ADDED_INSTEAD",
    )

    assert result["current_streak"] == 0
    assert result["status"] == MasteryStatus.NEEDS_REVIEW.value
    assert result["error_patterns"]["MC_SUB_01_ADDED_INSTEAD"] == 2
