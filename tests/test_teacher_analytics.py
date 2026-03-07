from services.teacher_analytics import (
    build_teacher_bottlenecks_response,
    build_teacher_caps_coverage_response,
    build_teacher_heatmap_response,
)


def test_build_teacher_heatmap_response_aggregates_statuses():
    student_ids = ["s1", "s2", "s3"]
    mastery_rows = [
        {"student_id": "s1", "skill_id": "A", "status": "mastered"},
        {"student_id": "s2", "skill_id": "A", "status": "learning"},
        {"student_id": "s3", "skill_id": "A", "status": "needs_review"},
    ]

    payload = build_teacher_heatmap_response("class-1", student_ids, mastery_rows)

    assert payload.class_id == "class-1"
    assert payload.learners == 3
    assert payload.skills[0].skill_id == "A"
    assert payload.skills[0].mastered == 1
    assert payload.skills[0].learning == 1
    assert payload.skills[0].needs_review == 1
    assert payload.skills[0].unknown == 0


def test_build_teacher_bottlenecks_response_sorts_by_failure_rate():
    student_ids = ["s1", "s2"]
    attempt_rows = [
        {"student_id": "s1", "skill_id": "A", "is_correct": False, "error_type_detected": "E1"},
        {"student_id": "s2", "skill_id": "A", "is_correct": False, "error_type_detected": "E1"},
        {"student_id": "s1", "skill_id": "B", "is_correct": True, "error_type_detected": None},
        {"student_id": "s2", "skill_id": "B", "is_correct": False, "error_type_detected": "E2"},
    ]

    payload = build_teacher_bottlenecks_response("class-1", student_ids, attempt_rows, min_attempts=2)

    assert len(payload.bottlenecks) == 2
    assert payload.bottlenecks[0].skill_id == "A"
    assert payload.bottlenecks[0].failure_rate == 1.0
    assert payload.bottlenecks[0].top_error_type == "E1"


def test_build_teacher_caps_coverage_response_computes_topic_percentages():
    student_ids = ["s1"]
    mastery_rows = [
        {"student_id": "s1", "skill_id": "A", "status": "mastered"},
        {"student_id": "s1", "skill_id": "B", "status": "learning"},
    ]
    skills_rows = [
        {"skill_id": "A", "caps_reference": {"topic": "Fractions"}},
        {"skill_id": "B", "caps_reference": {"topic": "Fractions"}},
        {"skill_id": "C", "caps_reference": {"topic": "Algebra"}},
    ]

    payload = build_teacher_caps_coverage_response(
        "class-1",
        student_ids,
        mastery_rows,
        skills_rows,
    )

    assert payload.summary["skills_total"] == 3
    assert payload.summary["skills_mastered_by_class"] == 1
    assert payload.summary["overall_coverage_percent"] == 33.33

    fractions = [row for row in payload.coverage if row.topic == "Fractions"][0]
    assert fractions.skills_total == 2
    assert fractions.skills_mastered_by_class == 1
    assert fractions.coverage_percent == 50.0
