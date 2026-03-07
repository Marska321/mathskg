from core.database import supabase
from services.mastery_state import compute_mastery_update


def update_student_mastery(student_id: str, skill_id: str, is_correct: bool, error_type: str | None = None) -> str:
    """Updates a student's mastery record and returns the new status."""
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

    update_payload = compute_mastery_update(
        current_streak=current_streak,
        error_patterns=current_patterns,
        is_correct=is_correct,
        error_type=error_type,
    )

    try:
        if res.data:
            (
                supabase.table("student_mastery")
                .update(update_payload)
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
                        **update_payload,
                    }
                )
                .execute()
            )
    except Exception as exc:
        print("Mastery Upsert Failed:", exc)

    return str(update_payload["status"])
