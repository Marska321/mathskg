from typing import Any


def evaluate_attempt(
    student_answer: str,
    correct_answer: str,
    error_mapping: dict[str, str] | None = None,
) -> dict[str, Any]:
    normalized_student = student_answer.strip().lower()
    normalized_correct = correct_answer.strip().lower()

    is_correct = normalized_student == normalized_correct
    error_type = None

    if not is_correct:
        mapping = error_mapping or {}
        error_type = mapping.get(student_answer, "UNKNOWN_ERROR")

    return {
        "is_correct": is_correct,
        "error_type": error_type,
    }
