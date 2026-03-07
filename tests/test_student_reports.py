from services.student_reports import (
    build_mastery_response,
    build_repair_path_response,
    build_student_report_response,
)


def test_build_mastery_response_counts_statuses():
    rows = [
        {"skill_id": "A", "status": "mastered", "current_streak": 3},
        {"skill_id": "B", "status": "learning", "current_streak": 1},
        {"skill_id": "C", "status": "needs_review", "active_repair_path": ["X"]},
        {"skill_id": "D", "status": "not_a_status"},
    ]

    payload = build_mastery_response("student-1", rows)

    assert payload.student_id == "student-1"
    assert payload.summary["mastered"] == 1
    assert payload.summary["learning"] == 1
    assert payload.summary["needs_review"] == 1
    assert payload.summary["unknown"] == 1


def test_build_repair_path_response_filters_by_status_and_skill_id():
    rows = [
        {"skill_id": "A", "status": "needs_review", "active_repair_path": ["R1", "R2"]},
        {"skill_id": "B", "status": "needs_review", "active_repair_path": []},
        {"skill_id": "C", "status": "learning", "active_repair_path": ["R3"]},
    ]

    all_repairs = build_repair_path_response("student-1", rows)
    assert len(all_repairs.items) == 1
    assert all_repairs.items[0].source_skill_id == "A"

    filtered = build_repair_path_response("student-1", rows, skill_id="A")
    assert len(filtered.items) == 1
    assert filtered.items[0].repair_path == ["R1", "R2"]


def test_build_student_report_response_computes_accuracy_and_top_error():
    mastery_rows = [
        {"skill_id": "A", "status": "mastered"},
        {"skill_id": "B", "status": "needs_review", "active_repair_path": ["R1"]},
    ]
    attempts = [
        {"is_correct": True, "error_type_detected": None},
        {"is_correct": False, "error_type_detected": "MC_SUB_01_ADDED_INSTEAD"},
        {"is_correct": False, "error_type_detected": "MC_SUB_01_ADDED_INSTEAD"},
    ]

    payload = build_student_report_response("student-1", mastery_rows, attempts)

    assert payload.summary["total_attempts"] == 3
    assert payload.summary["correct_attempts"] == 1
    assert payload.summary["accuracy"] == 0.33
    assert payload.summary["top_error_type"] == "MC_SUB_01_ADDED_INSTEAD"
    assert payload.mastery_breakdown["mastered"] == 1
    assert payload.mastery_breakdown["needs_review"] == 1
    assert len(payload.recent_repairs) == 1
