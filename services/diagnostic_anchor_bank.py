from __future__ import annotations

import json
import random
from functools import lru_cache
from pathlib import Path
from typing import Callable, Iterable

from models.diagnostic_bank import DiagnosticAnchorQuestion


LOCAL_BANK_PATH = Path(__file__).resolve().parent.parent / 'data' / 'grade4_diagnostic_question_bank.json'


@lru_cache(maxsize=1)
def load_local_question_bank(path: str | Path = LOCAL_BANK_PATH) -> tuple[DiagnosticAnchorQuestion, ...]:
    file_path = Path(path)
    with file_path.open('r', encoding='utf-8-sig') as handle:
        raw_items = json.load(handle)
    return tuple(DiagnosticAnchorQuestion.model_validate(item) for item in raw_items)


def fetch_anchor_questions_for_skill(skill_id: str, repository=None) -> list[DiagnosticAnchorQuestion]:
    rows: list[dict] = []

    if repository is not None:
        try:
            response = (
                repository.table('diagnostic_question_bank')
                .select('*')
                .eq('skill_id', skill_id)
                .execute()
            )
            rows = [row for row in (response.data or []) if row.get('active', True)]
        except Exception:
            rows = []

    if rows:
        return [DiagnosticAnchorQuestion.model_validate(row) for row in rows]

    return [record for record in load_local_question_bank() if record.skill_id == skill_id and record.active]


def select_anchor_question_for_skill(
    skill_id: str,
    repository=None,
    chooser: Callable[[list[DiagnosticAnchorQuestion]], DiagnosticAnchorQuestion] = random.choice,
) -> DiagnosticAnchorQuestion | None:
    anchors = fetch_anchor_questions_for_skill(skill_id, repository=repository)
    if not anchors:
        return None
    return chooser(anchors)


def build_anchor_prompt(anchor: DiagnosticAnchorQuestion) -> dict:
    return {
        'question_id': anchor.question_id,
        'skill_id': anchor.skill_id,
        'domain': anchor.domain,
        'cluster': anchor.cluster,
        'question_text': anchor.question_text,
    }
