import json
from pathlib import Path

from scripts.seed_diagnostic_question_bank import build_payloads, load_question_bank


EXPECTED_DOMAIN_COUNTS = {
    'Place Value': 12,
    'Rounding': 6,
    'Addition': 12,
    'Subtraction': 12,
    'Multiplication Concepts': 10,
    'Division': 8,
    'Fractions': 16,
    'Decimals': 10,
    'Measurement': 10,
    'Geometry': 8,
    'Data & Probability': 16,
}


def test_load_question_bank_returns_120_valid_records():
    records = load_question_bank()
    assert len(records) == 120
    assert len({record.question_id for record in records}) == 120


def test_question_bank_matches_expected_domain_distribution():
    records = load_question_bank()
    counts = {}
    for record in records:
        counts[record.domain] = counts.get(record.domain, 0) + 1
    assert counts == EXPECTED_DOMAIN_COUNTS


def test_question_bank_skill_ids_exist_in_caps_graph():
    records = load_question_bank()
    graph_path = Path(__file__).resolve().parent.parent / 'caps_graph.json'
    with graph_path.open('r', encoding='utf-8') as handle:
        graph_records = json.load(handle)

    graph_skill_ids = {item['skill_id'] for item in graph_records}
    anchor_skill_ids = {record.skill_id for record in records}
    assert anchor_skill_ids.issubset(graph_skill_ids)


def test_build_payloads_returns_serializable_dicts():
    payloads = build_payloads(load_question_bank())
    assert payloads[0]['question_id'] == 'G4-DIAG-001'
    assert payloads[-1]['question_id'] == 'G4-DIAG-120'
    assert all(payload['active'] is True for payload in payloads)
