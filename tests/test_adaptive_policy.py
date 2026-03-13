from services.adaptive_policy import (
    decide_next_skill_policy,
    merge_diagnostic_estimates_into_mastery_rows,
    prioritize_repair_nodes,
)


def test_prioritize_repair_nodes_applies_error_specific_ordering():
    nodes = ['M2-S-049', 'M2-PV-040', 'X-OTHER']
    prioritized = prioritize_repair_nodes(nodes, 'MC_SUB_02_TENS_COLUMN_ERROR')
    assert prioritized[0] == 'M2-PV-040'


def test_merge_diagnostic_estimates_into_mastery_rows_adds_missing_skills():
    merged = merge_diagnostic_estimates_into_mastery_rows(
        student_mastery_rows=[],
        diagnostic_estimate_rows=[
            {
                'skill_id': 'A',
                'student_mastery_status': 'needs_review',
                'active_repair_path': ['P1'],
            }
        ],
    )

    assert merged == [
        {
            'skill_id': 'A',
            'status': 'needs_review',
            'active_repair_path': ['P1'],
        }
    ]


def test_decide_next_skill_policy_prefers_repair_over_other_states():
    rows = [
        {'skill_id': 'A', 'status': 'learning', 'active_repair_path': []},
        {'skill_id': 'B', 'status': 'needs_review', 'active_repair_path': ['P1', 'P2']},
    ]
    decision = decide_next_skill_policy(rows, edges=[])

    assert decision['policy'] == 'repair'
    assert decision['target_skill_id'] == 'P1'
    assert decision['source_skill_id'] == 'B'


def test_decide_next_skill_policy_uses_diagnostic_estimates_for_repair():
    decision = decide_next_skill_policy(
        student_mastery_rows=[],
        edges=[],
        diagnostic_estimate_rows=[
            {
                'skill_id': 'B',
                'student_mastery_status': 'needs_review',
                'active_repair_path': ['P1', 'P2'],
            }
        ],
    )

    assert decision['policy'] == 'repair'
    assert decision['target_skill_id'] == 'P1'
    assert decision['source_skill_id'] == 'B'


def test_decide_next_skill_policy_uses_review_when_in_progress_exists():
    rows = [
        {'skill_id': 'B', 'status': 'learning', 'active_repair_path': []},
        {'skill_id': 'A', 'status': 'learning', 'active_repair_path': []},
    ]
    decision = decide_next_skill_policy(rows, edges=[])

    assert decision['policy'] == 'review'
    assert decision['target_skill_id'] == 'A'


def test_decide_next_skill_policy_selects_new_skill_deterministically():
    rows = [
        {'skill_id': 'A', 'status': 'mastered', 'active_repair_path': []},
    ]
    edges = [
        {'skill_id': 'B', 'prerequisite_id': 'A'},
        {'skill_id': 'C', 'prerequisite_id': 'A'},
    ]
    decision = decide_next_skill_policy(rows, edges)

    assert decision['policy'] == 'new'
    assert decision['target_skill_id'] == 'B'


def test_decide_next_skill_policy_complete_when_no_candidates():
    rows = [
        {'skill_id': 'A', 'status': 'mastered', 'active_repair_path': []},
    ]
    edges = []
    decision = decide_next_skill_policy(rows, edges)

    assert decision['policy'] == 'complete'
    assert decision['target_skill_id'] is None
