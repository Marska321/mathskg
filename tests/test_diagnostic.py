import pytest

from models.diagnostic_bank import DiagnosticAnchorQuestion
from models.domain import MasteryStatus
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
from services.diagnostic_orchestrator import (
    MAX_QUESTIONS,
    build_starting_skill_queue,
    select_next_anchor_question,
    should_complete_diagnostic,
)
from services.diagnostic_persistence import (
    build_diagnostic_item_payload,
    build_skill_estimate_payloads,
)


def _sample_edges() -> list[dict[str, str]]:
    return [
        {'skill_id': 'M4-N-002', 'prerequisite_id': 'M4-N-001'},
        {'skill_id': 'M4-N-003', 'prerequisite_id': 'M4-N-002'},
        {'skill_id': 'M4-F-001', 'prerequisite_id': 'M4-N-001'},
    ]


def _sample_records() -> list[dict]:
    return [
        {'skill_id': 'A', 'skill_name': 'A', 'difficulty': 1.0, 'prerequisites': []},
        {'skill_id': 'B', 'skill_name': 'B', 'difficulty': 2.0, 'prerequisites': ['A']},
        {'skill_id': 'C', 'skill_name': 'C', 'difficulty': 3.0, 'prerequisites': ['A']},
        {'skill_id': 'D', 'skill_name': 'D', 'difficulty': 2.5, 'prerequisites': ['B']},
    ]


def _domain_records() -> list[dict]:
    return [
        {'skill_id': 'M4-N-900', 'skill_name': 'Numbers terminal', 'difficulty': 3.0, 'prerequisites': ['M4-N-001']},
        {'skill_id': 'M4-F-900', 'skill_name': 'Fractions terminal', 'difficulty': 2.5, 'prerequisites': ['M4-F-001']},
        {'skill_id': 'M4-M-900', 'skill_name': 'Measurement terminal', 'difficulty': 2.0, 'prerequisites': ['M4-M-001']},
        {'skill_id': 'M4-N-901', 'skill_name': 'Another numbers terminal', 'difficulty': 2.8, 'prerequisites': ['M4-N-002']},
        {'skill_id': 'M4-N-001', 'skill_name': 'Numbers foundation', 'difficulty': 1.0, 'prerequisites': []},
        {'skill_id': 'M4-F-001', 'skill_name': 'Fractions foundation', 'difficulty': 1.0, 'prerequisites': []},
        {'skill_id': 'M4-M-001', 'skill_name': 'Measurement foundation', 'difficulty': 1.0, 'prerequisites': []},
        {'skill_id': 'M4-N-002', 'skill_name': 'Numbers second foundation', 'difficulty': 1.0, 'prerequisites': []},
    ]


def _anchor(skill_id: str, question_id: str) -> DiagnosticAnchorQuestion:
    return DiagnosticAnchorQuestion(
        question_id=question_id,
        grade_level=4,
        domain='Test',
        cluster='Test cluster',
        skill_id=skill_id,
        question_text=f'Question for {skill_id}',
        correct_answer='42',
        difficulty=1.0,
        active=True,
    )


def test_diagnostic_graph_loads_caps_graph_json():
    graph = DiagnosticGraph()
    assert 'M4-N-001' in graph.skills_by_id
    assert graph.get_starting_nodes()


def test_get_starting_nodes_returns_terminal_nodes_by_difficulty_then_skill_id():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.terminal_skill_ids == ('C', 'D')
    assert graph.get_starting_nodes() == ['C', 'D']


def test_evaluate_answer_incorrect_returns_immediate_prerequisites_only():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.evaluate_answer('D', False) == ['B']


def test_evaluate_answer_correct_moves_horizontally_to_other_terminal_nodes():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.evaluate_answer('C', True) == ['D']
    assert graph.assumed_known_skill_ids == {'A'}


def test_evaluate_answer_excludes_previously_tested_skills_on_later_calls():
    graph = DiagnosticGraph.from_records(_sample_records())
    assert graph.evaluate_answer('C', True) == ['D']
    assert graph.evaluate_answer('D', True) == []


def test_evaluate_answer_raises_for_unknown_skill_id():
    graph = DiagnosticGraph.from_records(_sample_records())
    with pytest.raises(ValueError, match='Unknown skill_id'):
        graph.evaluate_answer('missing', True)


def test_build_starting_skill_queue_spreads_domains():
    graph = DiagnosticGraph.from_records(_domain_records())
    current_state = initialize_diagnostic_state(graph.get_sorted_skill_ids())
    assert build_starting_skill_queue(graph, current_state) == ['M4-N-900', 'M4-F-900', 'M4-M-900']


def test_select_next_anchor_question_skips_missing_anchor_fetches():
    graph = DiagnosticGraph.from_records(_domain_records())
    current_state = initialize_diagnostic_state(graph.get_sorted_skill_ids())

    def fetch_anchor(skill_id: str):
        if skill_id == 'M4-N-900':
            return None
        if skill_id == 'M4-F-900':
            return _anchor(skill_id, 'Q-F')
        return None

    next_skill_id, anchor, remaining_queue = select_next_anchor_question(
        graph,
        current_state,
        ['M4-N-900', 'M4-F-900'],
        [],
        fetch_anchor,
    )

    assert next_skill_id == 'M4-F-900'
    assert anchor is not None
    assert anchor.question_id == 'Q-F'
    assert remaining_queue == []


def test_should_complete_diagnostic_when_cap_reached():
    current_state = {'A': 'unknown'}
    assert should_complete_diagnostic(current_state, question_count=MAX_QUESTIONS)


def test_build_diagnostic_item_payload_tracks_anchor_and_answer():
    payload = build_diagnostic_item_payload(
        diagnostic_session_id='session-1',
        student_id='student-1',
        question_order=3,
        anchor=_anchor('M4-F-900', 'Q-3'),
        student_answer='1/4',
        is_correct=True,
    )

    assert payload['diagnostic_session_id'] == 'session-1'
    assert payload['question_id'] == 'Q-3'
    assert payload['student_answer'] == '1/4'
    assert payload['is_correct'] is True


def test_build_skill_estimate_payloads_maps_states_to_mastery_statuses():
    payloads = build_skill_estimate_payloads(
        diagnostic_session_id='session-1',
        student_id='student-1',
        current_state={
            'A': MasteryStatus.MASTERED.value,
            'B': MasteryStatus.GAP.value,
            'C': MasteryStatus.LEARNING.value,
            'D': MasteryStatus.UNKNOWN.value,
        },
    )

    by_skill = {payload['skill_id']: payload for payload in payloads}
    assert by_skill['A']['mastery_status'] == 'mastered'
    assert by_skill['A']['student_mastery_status'] == MasteryStatus.MASTERED.value
    assert by_skill['B']['mastery_status'] == 'remediation'
    assert by_skill['B']['student_mastery_status'] == MasteryStatus.NEEDS_REVIEW.value
    assert by_skill['C']['mastery_status'] == 'learning'
    assert 'D' not in by_skill


def test_initialize_diagnostic_state_sets_unknown_for_all_skills():
    state = initialize_diagnostic_state(['A', 'B', 'C'])
    assert state == {'A': 'unknown', 'B': 'unknown', 'C': 'unknown'}


def test_get_all_prerequisites_traverses_full_upstream_path():
    prereqs = get_all_prerequisites('M4-N-003', _sample_edges())
    assert prereqs == {'M4-N-001', 'M4-N-002'}


def test_get_all_downstream_dependencies_traverses_full_downstream_path():
    deps = get_all_downstream_dependencies('M4-N-001', _sample_edges())
    assert deps == {'M4-N-002', 'M4-N-003', 'M4-F-001'}


def test_process_diagnostic_answer_correct_sets_mastery_and_assumed_prereqs():
    current_state = {
        'M4-N-001': 'unknown',
        'M4-N-002': 'unknown',
        'M4-N-003': 'unknown',
        'M4-F-001': 'unknown',
    }

    updated = process_diagnostic_answer('M4-N-003', True, current_state, _sample_edges())

    assert updated['M4-N-003'] == 'mastered'
    assert updated['M4-N-002'] == 'assumed_mastered'
    assert updated['M4-N-001'] == 'assumed_mastered'
    assert updated['M4-F-001'] == 'unknown'


def test_process_diagnostic_answer_incorrect_sets_gap_and_assumed_downstream():
    current_state = {
        'M4-N-001': 'unknown',
        'M4-N-002': 'unknown',
        'M4-N-003': 'unknown',
        'M4-F-001': 'unknown',
    }

    updated = process_diagnostic_answer('M4-N-001', False, current_state, _sample_edges())

    assert updated['M4-N-001'] == 'gap'
    assert updated['M4-N-002'] == 'assumed_gap'
    assert updated['M4-N-003'] == 'assumed_gap'
    assert updated['M4-F-001'] == 'assumed_gap'


def test_is_diagnostic_complete_when_question_limit_reached():
    state = {'A': 'unknown'}
    assert is_diagnostic_complete(state, question_count=30, max_questions=30)


def test_is_diagnostic_complete_when_all_nodes_known():
    state = {'A': 'mastered', 'B': 'gap'}
    assert is_diagnostic_complete(state, question_count=2, max_questions=30)


def test_calculate_node_weight_uses_worst_case_information_gain():
    state = {
        'M4-N-001': 'unknown',
        'M4-N-002': 'unknown',
        'M4-N-003': 'unknown',
        'M4-F-001': 'unknown',
    }
    weight = calculate_node_weight('M4-N-002', state, _sample_edges())
    assert weight == 1


def test_select_next_diagnostic_skill_prefers_terminal_unknown_nodes():
    state = {
        'M4-N-001': 'unknown',
        'M4-N-002': 'unknown',
        'M4-N-003': 'unknown',
        'M4-F-001': 'unknown',
    }
    next_skill = select_next_diagnostic_skill(state, _sample_edges())
    assert next_skill == 'M4-F-001'
