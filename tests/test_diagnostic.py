import pytest

from services.diagnostic_engine import (
    DiagnosticGraph,
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


def _sample_records() -> list[dict]:
    return [
        {"skill_id": "A", "skill_name": "A", "difficulty": 1.0, "prerequisites": []},
        {"skill_id": "B", "skill_name": "B", "difficulty": 2.0, "prerequisites": ["A"]},
        {"skill_id": "C", "skill_name": "C", "difficulty": 3.0, "prerequisites": ["A"]},
        {"skill_id": "D", "skill_name": "D", "difficulty": 2.5, "prerequisites": ["B"]},
    ]


def test_diagnostic_graph_loads_caps_graph_json():
    graph = DiagnosticGraph()
    assert "M4-N-001" in graph.skills_by_id
    assert graph.get_starting_nodes()


def test_get_starting_nodes_returns_terminal_nodes_by_difficulty_then_skill_id():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.terminal_skill_ids == ("C", "D")
    assert graph.get_starting_nodes() == ["C", "D"]


def test_evaluate_answer_incorrect_returns_immediate_prerequisites_only():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.evaluate_answer("D", False) == ["B"]


def test_evaluate_answer_correct_moves_horizontally_to_other_terminal_nodes():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.evaluate_answer("C", True) == ["D"]
    assert graph.assumed_known_skill_ids == {"A"}


def test_evaluate_answer_excludes_previously_tested_skills_on_later_calls():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.evaluate_answer("C", True) == ["D"]
    assert graph.evaluate_answer("D", True) == []


def test_evaluate_answer_raises_for_unknown_skill_id():
    graph = DiagnosticGraph.from_records(_sample_records())
    with pytest.raises(ValueError, match="Unknown skill_id"):
        graph.evaluate_answer("missing", True)


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


def test_select_next_diagnostic_skill_prefers_terminal_unknown_nodes():
    state = {
        "M4-N-001": "unknown",
        "M4-N-002": "unknown",
        "M4-N-003": "unknown",
        "M4-F-001": "unknown",
    }
    next_skill = select_next_diagnostic_skill(state, _sample_edges())
    assert next_skill == "M4-F-001"
