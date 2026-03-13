import os
from copy import deepcopy

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

os.environ.setdefault('SUPABASE_URL', 'https://example.supabase.co')
os.environ.setdefault('SUPABASE_KEY', 'test-key')

from routers import authoring as authoring_router_module
from routers import diagnostic as diagnostic_router_module
from routers import students as students_router_module
from routers import submission as submission_router_module
from routers import teacher as teacher_router_module
from services.diagnostic_engine import DiagnosticGraph
from services import diagnostic_session_store
from services import graph_service


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, db, table_name):
        self.db = db
        self.table_name = table_name
        self._filters = []
        self._selected = '*'
        self._limit = None
        self._op = 'select'
        self._payload = None
        self._on_conflict = None

    def select(self, fields):
        self._selected = fields
        self._op = 'select'
        return self

    def eq(self, key, value):
        self._filters.append((key, value))
        return self

    def limit(self, value):
        self._limit = value
        return self

    def insert(self, payload):
        self._op = 'insert'
        self._payload = payload
        return self

    def upsert(self, payload, on_conflict=None):
        self._op = 'upsert'
        self._payload = payload
        self._on_conflict = on_conflict
        return self

    def update(self, payload):
        self._op = 'update'
        self._payload = payload
        return self

    def execute(self):
        if self.table_name not in self.db.tables:
            self.db.tables[self.table_name] = []

        table_rows = self.db.tables[self.table_name]

        if self._op == 'select':
            rows = [deepcopy(row) for row in table_rows if self._match(row)]
            rows = self._project(rows)
            if self._limit is not None:
                rows = rows[: self._limit]
            return FakeResponse(rows)

        if self._op == 'insert':
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            created = []
            for payload in payloads:
                row = deepcopy(payload)
                table_rows.append(row)
                created.append(row)
            return FakeResponse(created)

        if self._op == 'update':
            updated = []
            for row in table_rows:
                if self._match(row):
                    row.update(deepcopy(self._payload))
                    updated.append(deepcopy(row))
            return FakeResponse(updated)

        if self._op == 'upsert':
            payloads = self._payload if isinstance(self._payload, list) else [self._payload]
            results = []
            for payload in payloads:
                row = deepcopy(payload)
                conflict_keys = self._conflict_keys(row)
                existing = self._find_existing(table_rows, row, conflict_keys)
                if existing is None:
                    table_rows.append(row)
                    results.append(deepcopy(row))
                else:
                    existing.update(row)
                    results.append(deepcopy(existing))
            return FakeResponse(results)

        return FakeResponse([])

    def _match(self, row):
        return all(row.get(key) == value for key, value in self._filters)

    def _project(self, rows):
        if self._selected == '*':
            return rows

        fields = [field.strip() for field in self._selected.split(',')]
        projected = []
        for row in rows:
            projected.append({field: row.get(field) for field in fields})
        return projected

    def _conflict_keys(self, row):
        if self._on_conflict:
            return [key.strip() for key in self._on_conflict.split(',')]

        defaults = {
            'skills': ['skill_id'],
            'student_mastery': ['student_id', 'skill_id'],
            'skill_prerequisites': ['skill_id', 'prerequisite_id'],
            'question_templates': ['template_id'],
            'diagnostic_sessions': ['session_id'],
            'class_students': ['class_id', 'student_id'],
            'diagnostic_question_bank': ['question_id'],
            'diagnostic_skill_estimates': ['diagnostic_session_id', 'skill_id'],
        }
        keys = defaults.get(self.table_name, [])
        return [key for key in keys if key in row]

    def _find_existing(self, table_rows, row, conflict_keys):
        if not conflict_keys:
            return None
        for existing in table_rows:
            if all(existing.get(key) == row.get(key) for key in conflict_keys):
                return existing
        return None


class FakeSupabase:
    def __init__(self, seed=None):
        self.tables = deepcopy(seed or {})

    def table(self, table_name):
        return FakeQuery(self, table_name)


@pytest.fixture
def client_and_db(monkeypatch):
    seed = {
        'skills': [
            {'skill_id': 'M4-N-014', 'skill_name': 'Subtract', 'caps_reference': {'topic': 'Number'}, 'approval_status': 'pending', 'difficulty': 1.0},
            {'skill_id': 'M4-F-001', 'skill_name': 'Equal parts', 'caps_reference': {'topic': 'Fractions'}, 'approval_status': 'pending', 'difficulty': 1.0},
        ],
        'skill_prerequisites': [
            {'skill_id': 'M4-F-001', 'prerequisite_id': 'M4-N-014'},
        ],
        'student_mastery': [
            {'student_id': 's1', 'skill_id': 'M4-N-014', 'status': 'mastered', 'current_streak': 3, 'error_patterns': {}, 'active_repair_path': []},
            {'student_id': 's1', 'skill_id': 'M4-F-001', 'status': 'needs_review', 'current_streak': 0, 'error_patterns': {'E1': 1}, 'active_repair_path': ['M4-N-014']},
            {'student_id': 's2', 'skill_id': 'M4-N-014', 'status': 'learning', 'current_streak': 1, 'error_patterns': {}, 'active_repair_path': []},
        ],
        'attempt_logs': [
            {'student_id': 's1', 'skill_id': 'M4-N-014', 'is_correct': True, 'error_type_detected': None},
            {'student_id': 's1', 'skill_id': 'M4-F-001', 'is_correct': False, 'error_type_detected': 'E1'},
            {'student_id': 's2', 'skill_id': 'M4-N-014', 'is_correct': False, 'error_type_detected': 'E2'},
        ],
        'class_students': [
            {'class_id': 'class-1', 'student_id': 's1'},
            {'class_id': 'class-1', 'student_id': 's2'},
        ],
        'question_templates': [],
        'diagnostic_question_bank': [
            {
                'question_id': 'Q-N-014-1',
                'grade_level': 4,
                'domain': 'Subtraction',
                'cluster': 'two-digit subtraction',
                'skill_id': 'M4-N-014',
                'question_text': '63 - 27 = ?',
                'correct_answer': '36',
                'difficulty': 1.0,
                'active': True,
            },
            {
                'question_id': 'Q-F-001-1',
                'grade_level': 4,
                'domain': 'Fractions',
                'cluster': 'equal parts',
                'skill_id': 'M4-F-001',
                'question_text': 'Which fraction shows one equal part out of four?',
                'correct_answer': '1/4',
                'difficulty': 1.0,
                'active': True,
            },
        ],
        'diagnostic_items': [],
        'diagnostic_skill_estimates': [],
        'diagnostic_sessions': [],
    }

    fake_db = FakeSupabase(seed)

    monkeypatch.setattr(authoring_router_module, 'supabase', fake_db)
    monkeypatch.setattr(students_router_module, 'supabase', fake_db)
    monkeypatch.setattr(teacher_router_module, 'supabase', fake_db)
    monkeypatch.setattr(submission_router_module, 'supabase', fake_db)
    monkeypatch.setattr(diagnostic_router_module, 'supabase_client', fake_db)
    monkeypatch.setattr(
        diagnostic_router_module,
        '_build_graph',
        lambda: DiagnosticGraph.from_records(
            [
                {'skill_id': 'M4-N-014', 'skill_name': 'Subtract', 'difficulty': 1.0, 'prerequisites': []},
                {'skill_id': 'M4-F-001', 'skill_name': 'Equal parts', 'difficulty': 2.0, 'prerequisites': ['M4-N-014']},
            ]
        ),
    )
    monkeypatch.setattr(diagnostic_session_store, 'supabase', fake_db)
    monkeypatch.setattr(graph_service, 'supabase', fake_db)
    monkeypatch.setattr(diagnostic_session_store, '_USE_MEMORY_ONLY', False)
    monkeypatch.setattr(diagnostic_session_store, '_MEMORY_SESSIONS', {})

    app = FastAPI()
    app.include_router(diagnostic_router_module.router)
    app.include_router(submission_router_module.router)
    app.include_router(students_router_module.router)
    app.include_router(teacher_router_module.router)
    app.include_router(authoring_router_module.router)

    return TestClient(app), fake_db


def test_diagnostic_flow_endpoints_persist_items_and_estimates(client_and_db):
    client, db = client_and_db

    start = client.post('/diagnostic/start', json={'student_id': 's2'})
    assert start.status_code == 200
    start_body = start.json()
    assert start_body['status'] == 'in_progress'
    assert start_body['question']['question_id'] == 'Q-F-001-1'

    answer = client.post(
        '/diagnostic/answer',
        json={
            'session_id': start_body['session_id'],
            'skill_id': start_body['next_skill'],
            'student_answer': '1/4',
            'is_correct': True,
        },
    )
    assert answer.status_code == 200
    answer_body = answer.json()
    assert answer_body['status'] == 'complete'

    assert len(db.tables['diagnostic_items']) == 1
    item = db.tables['diagnostic_items'][0]
    assert item['diagnostic_session_id'] == start_body['session_id']
    assert item['question_id'] == 'Q-F-001-1'
    assert item['student_answer'] == '1/4'
    assert item['is_correct'] is True

    estimate_rows = db.tables['diagnostic_skill_estimates']
    assert {row['skill_id'] for row in estimate_rows} == {'M4-N-014', 'M4-F-001'}
    by_skill = {row['skill_id']: row for row in estimate_rows}
    assert by_skill['M4-F-001']['mastery_status'] == 'mastered'
    assert by_skill['M4-N-014']['mastery_status'] == 'learning'

    mastery_rows = [
        row for row in db.tables['student_mastery']
        if row['student_id'] == 's2'
    ]
    mastery_by_skill = {row['skill_id']: row for row in mastery_rows}
    assert mastery_by_skill['M4-F-001']['status'] == 'mastered'
    assert mastery_by_skill['M4-F-001']['active_repair_path'] == []
    assert mastery_by_skill['M4-N-014']['status'] == 'learning'


def test_diagnostic_remediation_handoff_populates_repair_path_for_next_skill(client_and_db):
    client, db = client_and_db

    start = client.post('/diagnostic/start', json={'student_id': 's2'})
    assert start.status_code == 200
    start_body = start.json()

    answer = client.post(
        '/diagnostic/answer',
        json={
            'session_id': start_body['session_id'],
            'skill_id': start_body['next_skill'],
            'student_answer': '2/4',
            'is_correct': False,
        },
    )
    assert answer.status_code == 200
    assert answer.json()['status'] == 'complete'

    mastery_rows = [
        row for row in db.tables['student_mastery']
        if row['student_id'] == 's2'
    ]
    mastery_by_skill = {row['skill_id']: row for row in mastery_rows}
    assert mastery_by_skill['M4-F-001']['status'] == 'needs_review'
    assert mastery_by_skill['M4-F-001']['active_repair_path'] == ['M4-N-014']

    next_skill = client.get('/next-skill', params={'student_id': 's2'})
    assert next_skill.status_code == 200
    body = next_skill.json()
    assert body['policy'] == 'repair'
    assert body['source_skill_id'] == 'M4-F-001'
    assert body['skill']['skill_id'] == 'M4-N-014'


def test_diagnostic_flow_completes_at_max_question_cap(client_and_db):
    client, db = client_and_db
    db.tables['diagnostic_sessions'].append(
        {
            'session_id': 'cap-session',
            'student_id': 's2',
            'status': 'in_progress',
            'current_state': {'M4-N-014': 'unknown'},
            'question_count': 24,
            'asked_skills': [],
            'pending_skill_ids': [],
            'active_question': {
                'question_id': 'Q-N-014-1',
                'grade_level': 4,
                'domain': 'Subtraction',
                'cluster': 'two-digit subtraction',
                'skill_id': 'M4-N-014',
                'question_text': '63 - 27 = ?',
                'correct_answer': '36',
                'difficulty': 1.0,
                'active': True,
            },
            'next_skill_id': 'M4-N-014',
            'placement_skill_id': None,
            'confidence': None,
            'created_at': '2026-03-13T00:00:00+00:00',
            'updated_at': '2026-03-13T00:00:00+00:00',
        }
    )

    answer = client.post(
        '/diagnostic/answer',
        json={
            'session_id': 'cap-session',
            'skill_id': 'M4-N-014',
            'student_answer': '36',
            'is_correct': True,
        },
    )
    assert answer.status_code == 200
    assert answer.json()['status'] == 'complete'
    assert len(db.tables['diagnostic_items']) == 1
    assert len(db.tables['diagnostic_skill_estimates']) >= 1


def test_students_endpoints(client_and_db):
    client, _ = client_and_db

    mastery = client.get('/students/s1/mastery')
    assert mastery.status_code == 200
    mastery_body = mastery.json()
    assert mastery_body['student_id'] == 's1'
    assert 'summary' in mastery_body

    repairs = client.get('/students/s1/repair-path')
    assert repairs.status_code == 200
    assert repairs.json()['student_id'] == 's1'

    report = client.get('/students/s1/report')
    assert report.status_code == 200
    report_body = report.json()
    assert report_body['summary']['total_attempts'] >= 1


def test_teacher_endpoints(client_and_db):
    client, _ = client_and_db

    heatmap = client.get('/teacher/class/class-1/heatmap')
    assert heatmap.status_code == 200
    assert heatmap.json()['class_id'] == 'class-1'

    bottlenecks = client.get('/teacher/class/class-1/bottlenecks')
    assert bottlenecks.status_code == 200
    assert 'bottlenecks' in bottlenecks.json()

    coverage = client.get('/teacher/class/class-1/caps-coverage')
    assert coverage.status_code == 200
    assert 'coverage' in coverage.json()


def test_authoring_endpoints(client_and_db):
    client, db = client_and_db

    list_resp = client.get('/authoring/skills')
    assert list_resp.status_code == 200

    create_skill = client.post(
        '/authoring/skills',
        json={
            'skill_id': 'M4-N-099',
            'skill_name': 'New skill',
            'difficulty': 1.2,
            'approval_status': 'pending',
        },
    )
    assert create_skill.status_code == 200

    update_skill = client.put(
        '/authoring/skills/M4-N-099',
        json={'approval_status': 'review'},
    )
    assert update_skill.status_code == 200

    create_template = client.post(
        '/authoring/templates',
        json={
            'skill_id': 'M4-N-099',
            'template_id': 'TPL-M4-N-099-1',
            'template_body': {'kind': 'mcq'},
            'version': 1,
            'status': 'draft',
        },
    )
    assert create_template.status_code == 200

    publish = client.post(
        '/authoring/publish',
        json={'skill_id': 'M4-N-099', 'force': False},
    )
    assert publish.status_code == 200
    assert publish.json()['status'] == 'published'

    skill_rows = db.tables['skills']
    published = [row for row in skill_rows if row.get('skill_id') == 'M4-N-099'][0]
    assert published['approval_status'] == 'live'

