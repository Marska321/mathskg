from core.database import supabase
from models.domain import MasteryStatus


def update_student_mastery(student_id: str, skill_id: str, is_correct: bool, error_type: str | None = None) -> str:
    """Upgrades or downgrades a student's mastery state based on an answer."""
    res = (
        supabase.table("student_mastery")
        .select("id, current_streak, error_patterns")
        .eq("student_id", student_id)
        .eq("skill_id", skill_id)
        .execute()
    )

    current_streak = 0
    current_patterns: dict[str, int] = {}

    if res.data:
        record = res.data[0]
        current_streak = record.get("current_streak") or 0
        current_patterns = record.get("error_patterns") or {}
        if not isinstance(current_patterns, dict):
            current_patterns = {}

    new_streak = current_streak + 1 if is_correct else 0

    if not is_correct and error_type:
        current_patterns[error_type] = current_patterns.get(error_type, 0) + 1

    if new_streak >= 3:
        new_status = MasteryStatus.MASTERED.value
    elif new_streak > 0 or is_correct:
        new_status = MasteryStatus.LEARNING.value
    else:
        new_status = MasteryStatus.NEEDS_REVIEW.value

    try:
        if res.data:
            (
                supabase.table("student_mastery")
                .update(
                    {
                        "current_streak": new_streak,
                        "status": new_status,
                        "error_patterns": current_patterns,
                    }
                )
                .eq("student_id", student_id)
                .eq("skill_id", skill_id)
                .execute()
            )
        else:
            (
                supabase.table("student_mastery")
                .insert(
                    {
                        "student_id": student_id,
                        "skill_id": skill_id,
                        "current_streak": new_streak,
                        "status": new_status,
                        "error_patterns": current_patterns,
                    }
                )
                .execute()
            )
    except Exception as exc:
        print("Mastery Upsert Failed:", exc)

    return new_status
