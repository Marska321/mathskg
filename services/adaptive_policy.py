from collections import defaultdict

from models.domain import MasteryStatus


def prioritize_repair_nodes(repair_nodes: list[str], error_type: str | None) -> list[str]:
    ordered = list(repair_nodes)
    if not ordered:
        return ordered

    if error_type == 'MC_SUB_02_TENS_COLUMN_ERROR' and 'M2-PV-040' in ordered:
        ordered.remove('M2-PV-040')
        ordered.insert(0, 'M2-PV-040')
    elif error_type == 'MC_SUB_01_ADDED_INSTEAD' and 'M2-S-049' in ordered:
        ordered.remove('M2-S-049')
        ordered.insert(0, 'M2-S-049')

    return ordered


def merge_diagnostic_estimates_into_mastery_rows(
    student_mastery_rows: list[dict],
    diagnostic_estimate_rows: list[dict] | None = None,
) -> list[dict]:
    merged: dict[str, dict] = {
        row['skill_id']: {
            'skill_id': row['skill_id'],
            'status': row.get('status'),
            'active_repair_path': list(row.get('active_repair_path') or []),
        }
        for row in student_mastery_rows
    }

    for estimate in diagnostic_estimate_rows or []:
        skill_id = estimate['skill_id']
        target = merged.setdefault(
            skill_id,
            {
                'skill_id': skill_id,
                'status': estimate.get('student_mastery_status'),
                'active_repair_path': [],
            },
        )

        target['status'] = estimate.get('student_mastery_status', target.get('status'))
        if isinstance(estimate.get('active_repair_path'), list) and estimate['active_repair_path']:
            target['active_repair_path'] = list(estimate['active_repair_path'])

    return sorted(merged.values(), key=lambda row: row['skill_id'])


def decide_next_skill_policy(
    student_mastery_rows: list[dict],
    edges: list[dict],
    diagnostic_estimate_rows: list[dict] | None = None,
) -> dict:
    rows = merge_diagnostic_estimates_into_mastery_rows(student_mastery_rows, diagnostic_estimate_rows)

    repair_candidates = [
        row
        for row in rows
        if row.get('status') == MasteryStatus.NEEDS_REVIEW.value
        and isinstance(row.get('active_repair_path'), list)
        and len(row.get('active_repair_path')) > 0
    ]
    if repair_candidates:
        first = repair_candidates[0]
        return {
            'policy': 'repair',
            'target_skill_id': first['active_repair_path'][0],
            'source_skill_id': first['skill_id'],
            'reason': 'needs_review skill has an active repair path',
        }

    review_candidates = [
        row
        for row in rows
        if row.get('status') in (MasteryStatus.LEARNING.value, MasteryStatus.NEEDS_REVIEW.value)
    ]
    if review_candidates:
        first = review_candidates[0]
        return {
            'policy': 'review',
            'target_skill_id': first['skill_id'],
            'source_skill_id': first['skill_id'],
            'reason': 'student has in-progress learning/review skills',
        }

    mastered_skills = {
        row['skill_id']
        for row in rows
        if row.get('status') == MasteryStatus.MASTERED.value
    }

    prereqs_by_skill: dict[str, set[str]] = defaultdict(set)
    all_skill_ids: set[str] = set(mastered_skills)
    for edge in edges:
        skill_id = edge['skill_id']
        prereq_id = edge['prerequisite_id']
        prereqs_by_skill[skill_id].add(prereq_id)
        all_skill_ids.add(skill_id)
        all_skill_ids.add(prereq_id)

    available_skills = []
    for skill_id in sorted(all_skill_ids):
        if skill_id in mastered_skills:
            continue
        prereqs = prereqs_by_skill.get(skill_id, set())
        if all(prereq in mastered_skills for prereq in prereqs):
            available_skills.append(skill_id)

    if available_skills:
        return {
            'policy': 'new',
            'target_skill_id': available_skills[0],
            'source_skill_id': None,
            'reason': 'all prerequisites are mastered',
        }

    return {
        'policy': 'complete',
        'target_skill_id': None,
        'source_skill_id': None,
        'reason': 'no eligible skills remain',
    }
