from services.diagnostic_result import build_diagnostic_result


def test_build_diagnostic_result_prefers_gap_for_placement():
    state = {
        "A": "gap",
        "B": "mastered",
        "C": "assumed_mastered",
        "D": "unknown",
    }
    result = build_diagnostic_result(state, question_count=4)

    assert result["placement_skill_id"] == "A"
    assert result["resolved_count"] == 3
    assert result["skill_count"] == 4
    assert result["confidence"] == 0.75


def test_build_diagnostic_result_uses_highest_mastered_if_no_gaps():
    state = {
        "A": "mastered",
        "B": "assumed_mastered",
        "C": "unknown",
    }
    result = build_diagnostic_result(state, question_count=2)

    assert result["placement_skill_id"] == "B"
    assert result["gap_skills"] == []
    assert result["mastered_skills"] == ["A", "B"]


def test_build_diagnostic_result_handles_empty_state():
    result = build_diagnostic_result({}, question_count=0)

    assert result["placement_skill_id"] is None
    assert result["confidence"] == 0.0
    assert result["resolved_count"] == 0
    assert result["skill_count"] == 0
