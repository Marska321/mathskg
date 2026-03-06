from services.diagnostic_engine import (
    calculate_node_weight,
    get_all_downstream_dependencies,
    get_all_prerequisites,
    initialize_diagnostic_state,
    is_diagnostic_complete,
    process_diagnostic_answer,
    select_next_diagnostic_skill,
)


def _sample_edges() -> list[dict[str, str]]:
    return [
        {"skill_id": "M4-N-002", "prerequisite_id": "M4-N-001"},
        {"skill_id": "M4-N-003", "prerequisite_id": "M4-N-002"},
        {"skill_id": "M4-F-001", "prerequisite_id": "M4-N-001"},
    ]


def test_initialize_diagnostic_state_sets_unknown_for_all_skills():
    state = initialize_diagnostic_state(["A", "B", "C"])
    assert state == {"A": "unknown", "B": "unknown", "C": "unknown"}


def test_get_all_prerequisites_traverses_full_upstream_path():
    prereqs = get_all_prerequisites("M4-N-003", _sample_edges())
    assert prereqs == {"M4-N-001", "M4-N-002"}


def test_get_all_downstream_dependencies_traverses_full_downstream_path():
    deps = get_all_downstream_dependencies("M4-N-001", _sample_edges())
    assert deps == {"M4-N-002", "M4-N-003", "M4-F-001"}


def test_process_diagnostic_answer_correct_sets_mastery_and_assumed_prereqs():
    current_state = {
        "M4-N-001": "unknown",
        "M4-N-002": "unknown",
        "M4-N-003": "unknown",
        "M4-F-001": "unknown",
    }

    updated = process_diagnostic_answer("M4-N-003", True, current_state, _sample_edges())

    assert updated["M4-N-003"] == "mastered"
    assert updated["M4-N-002"] == "assumed_mastered"
    assert updated["M4-N-001"] == "assumed_mastered"
    assert updated["M4-F-001"] == "unknown"


def test_process_diagnostic_answer_incorrect_sets_gap_and_assumed_downstream():
    current_state = {
        "M4-N-001": "unknown",
        "M4-N-002": "unknown",
        "M4-N-003": "unknown",
        "M4-F-001": "unknown",
    }

    updated = process_diagnostic_answer("M4-N-001", False, current_state, _sample_edges())

    assert updated["M4-N-001"] == "gap"
    assert updated["M4-N-002"] == "assumed_gap"
    assert updated["M4-N-003"] == "assumed_gap"
    assert updated["M4-F-001"] == "assumed_gap"


def test_is_diagnostic_complete_when_question_limit_reached():
    state = {"A": "unknown"}
    assert is_diagnostic_complete(state, question_count=30, max_questions=30)


def test_is_diagnostic_complete_when_all_nodes_known():
    state = {"A": "mastered", "B": "gap"}
    assert is_diagnostic_complete(state, question_count=2, max_questions=30)


def test_calculate_node_weight_uses_worst_case_information_gain():
    state = {
        "M4-N-001": "unknown",
        "M4-N-002": "unknown",
        "M4-N-003": "unknown",
        "M4-F-001": "unknown",
    }
    weight = calculate_node_weight("M4-N-002", state, _sample_edges())
    assert weight == 1


def test_select_next_diagnostic_skill_picks_highest_weight_node():
    state = {
        "M4-N-001": "unknown",
        "M4-N-002": "unknown",
        "M4-N-003": "unknown",
        "M4-F-001": "unknown",
    }
    next_skill = select_next_diagnostic_skill(state, _sample_edges())
    assert next_skill == "M4-N-002"
