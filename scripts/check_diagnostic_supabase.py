import argparse
import json
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from postgrest.exceptions import APIError

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import get_supabase
from models.diagnostic_bank import DiagnosticAnchorQuestion
from scripts.seed_diagnostic_question_bank import load_question_bank
from services.diagnostic_engine import DiagnosticGraph


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    extra: dict[str, Any] | None = None


def run_query(client, table_name: str, fields: str = '*', limit: int | None = None):
    query = client.table(table_name).select(fields)
    if limit is not None:
        query = query.limit(limit)
    return query.execute().data or []


def check_table_exists(client: Client, table_name: str) -> CheckResult:
    try:
        rows = run_query(client, table_name, fields='*', limit=1)
    except APIError as exc:
        return CheckResult(
            name=f'table:{table_name}',
            ok=False,
            detail='table query failed',
            extra={'error': str(exc)},
        )
    return CheckResult(
        name=f'table:{table_name}',
        ok=True,
        detail='table reachable',
        extra={'sample_count': len(rows)},
    )


def check_question_bank(client: Client, local_bank: list[DiagnosticAnchorQuestion], graph: DiagnosticGraph) -> list[CheckResult]:
    results: list[CheckResult] = []
    local_by_skill = Counter(record.skill_id for record in local_bank)
    graph_ids = set(graph.skills_by_id)
    missing_local_graph_ids = sorted(set(local_by_skill) - graph_ids)
    results.append(
        CheckResult(
            name='local_bank_alignment',
            ok=not missing_local_graph_ids,
            detail='local anchor bank skill ids align with DiagnosticGraph' if not missing_local_graph_ids else 'local anchor bank has skill ids missing from DiagnosticGraph',
            extra={
                'local_question_count': len(local_bank),
                'unique_local_skill_ids': len(local_by_skill),
                'missing_graph_skill_ids_sample': missing_local_graph_ids[:10],
            },
        )
    )

    try:
        live_rows = run_query(client, 'diagnostic_question_bank', fields='question_id,skill_id,active')
    except APIError as exc:
        results.append(
            CheckResult(
                name='live_bank',
                ok=False,
                detail='diagnostic_question_bank query failed',
                extra={'error': str(exc)},
            )
        )
        return results

    live_active = [row for row in live_rows if row.get('active', True)]
    live_skill_ids = {row['skill_id'] for row in live_active if row.get('skill_id')}
    missing_live_graph_ids = sorted(live_skill_ids - graph_ids)
    results.append(
        CheckResult(
            name='live_bank_count',
            ok=len(live_rows) > 0,
            detail='diagnostic_question_bank contains rows' if live_rows else 'diagnostic_question_bank is empty',
            extra={
                'live_question_count': len(live_rows),
                'live_active_question_count': len(live_active),
                'live_unique_skill_ids': len(live_skill_ids),
            },
        )
    )
    results.append(
        CheckResult(
            name='live_bank_alignment',
            ok=not missing_live_graph_ids,
            detail='live anchor bank skill ids align with DiagnosticGraph' if not missing_live_graph_ids else 'live anchor bank has skill ids missing from DiagnosticGraph',
            extra={'missing_graph_skill_ids_sample': missing_live_graph_ids[:10]},
        )
    )
    return results


def check_skill_alignment(client: Client, graph: DiagnosticGraph) -> list[CheckResult]:
    results: list[CheckResult] = []
    graph_ids = set(graph.skills_by_id)

    try:
        live_skills = run_query(client, 'skills', fields='skill_id')
    except APIError as exc:
        return [
            CheckResult(
                name='skills_alignment',
                ok=False,
                detail='skills query failed',
                extra={'error': str(exc)},
            )
        ]

    live_skill_ids = {row['skill_id'] for row in live_skills if row.get('skill_id')}
    overlap = sorted(live_skill_ids & graph_ids)
    only_live = sorted(live_skill_ids - graph_ids)
    only_graph = sorted(graph_ids - live_skill_ids)

    results.append(
        CheckResult(
            name='skills_overlap',
            ok=len(overlap) > 0,
            detail='live skills overlap with DiagnosticGraph ids' if overlap else 'live skills do not overlap with DiagnosticGraph ids',
            extra={
                'live_skill_count': len(live_skill_ids),
                'graph_skill_count': len(graph_ids),
                'overlap_count': len(overlap),
                'live_only_sample': only_live[:10],
                'graph_only_sample': only_graph[:10],
            },
        )
    )

    try:
        edge_rows = run_query(client, 'skill_prerequisites', fields='*', limit=20)
    except APIError as exc:
        results.append(
            CheckResult(
                name='skill_prerequisites_shape',
                ok=False,
                detail='skill_prerequisites query failed',
                extra={'error': str(exc)},
            )
        )
        return results

    detected_columns = sorted({key for row in edge_rows for key in row.keys()})
    prerequisite_key = 'prerequisite_id' if any('prerequisite_id' in row for row in edge_rows) else 'prerequisite_skill_id' if any('prerequisite_skill_id' in row for row in edge_rows) else None
    results.append(
        CheckResult(
            name='skill_prerequisites_shape',
            ok=prerequisite_key is not None,
            detail=f'skill_prerequisites uses {prerequisite_key}' if prerequisite_key else 'skill_prerequisites prerequisite column not recognized',
            extra={
                'columns': detected_columns,
                'sample_rows': edge_rows[:3],
            },
        )
    )
    return results


def check_write_probes(client: Client) -> list[CheckResult]:
    probe_suffix = datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')
    session_id = f'diag-probe-{probe_suffix}'
    student_id = 'diag-probe-student'
    question_id = f'diag-probe-question-{probe_suffix}'
    skill_id = 'M4-N-001'

    item_payload = {
        'diagnostic_session_id': session_id,
        'student_id': student_id,
        'question_id': question_id,
        'skill_id': skill_id,
        'domain': 'Probe',
        'cluster': 'Probe',
        'question_text': 'Probe question',
        'question_order': 1,
        'student_answer': 'probe',
        'is_correct': True,
    }
    estimate_payload = {
        'diagnostic_session_id': session_id,
        'student_id': student_id,
        'skill_id': skill_id,
        'diagnostic_state': 'mastered',
        'estimated_mastery_probability': 0.95,
        'mastery_status': 'mastered',
        'student_mastery_status': 'mastered',
        'confidence_level': 'high',
        'source': 'direct',
    }

    results: list[CheckResult] = []
    try:
        client.table('diagnostic_items').insert(item_payload).execute()
        client.table('diagnostic_items').delete().eq('diagnostic_session_id', session_id).execute()
        results.append(CheckResult('write_probe:diagnostic_items', True, 'diagnostic_items write and cleanup succeeded'))
    except APIError as exc:
        results.append(
            CheckResult(
                'write_probe:diagnostic_items',
                False,
                'diagnostic_items write probe failed',
                extra={'error': str(exc), 'payload': item_payload},
            )
        )

    try:
        client.table('diagnostic_skill_estimates').upsert(
            estimate_payload,
            on_conflict='diagnostic_session_id,skill_id',
        ).execute()
        client.table('diagnostic_skill_estimates').delete().eq('diagnostic_session_id', session_id).execute()
        results.append(CheckResult('write_probe:diagnostic_skill_estimates', True, 'diagnostic_skill_estimates write and cleanup succeeded'))
    except APIError as exc:
        results.append(
            CheckResult(
                'write_probe:diagnostic_skill_estimates',
                False,
                'diagnostic_skill_estimates write probe failed',
                extra={'error': str(exc), 'payload': estimate_payload},
            )
        )
    return results


def build_report(write_probe: bool) -> dict[str, Any]:
    load_dotenv()
    client = get_supabase()
    graph = DiagnosticGraph()
    local_bank = load_question_bank()

    results: list[CheckResult] = []
    for table_name in ('diagnostic_question_bank', 'diagnostic_items', 'diagnostic_skill_estimates', 'skills', 'skill_prerequisites'):
        results.append(check_table_exists(client, table_name))
    results.extend(check_question_bank(client, local_bank, graph))
    results.extend(check_skill_alignment(client, graph))
    if write_probe:
        results.extend(check_write_probes(client))

    ok = all(result.ok for result in results)
    return {
        'ok': ok,
        'checked_at_utc': datetime.now(timezone.utc).isoformat(),
        'write_probe': write_probe,
        'results': [asdict(result) for result in results],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description='Verify diagnostic Supabase setup.')
    parser.add_argument(
        '--write-probe',
        action='store_true',
        help='Insert and clean up probe rows in diagnostic_items and diagnostic_skill_estimates.',
    )
    args = parser.parse_args()
    report = build_report(write_probe=args.write_probe)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
