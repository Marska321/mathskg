import json
import sys
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from supabase import Client, create_client

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.config import get_required_env
from models.diagnostic_bank import DiagnosticAnchorQuestion


DEFAULT_BANK_PATH = Path(__file__).resolve().parent.parent / 'data' / 'grade4_diagnostic_question_bank.json'


def load_question_bank(path: str | Path = DEFAULT_BANK_PATH) -> list[DiagnosticAnchorQuestion]:
    file_path = Path(path)
    with file_path.open('r', encoding='utf-8-sig') as handle:
        raw_items = json.load(handle)
    return [DiagnosticAnchorQuestion.model_validate(item) for item in raw_items]


def build_payloads(records: Iterable[DiagnosticAnchorQuestion]) -> list[dict]:
    return [record.model_dump() for record in records]


def create_supabase_client() -> Client:
    load_dotenv()
    return create_client(get_required_env('SUPABASE_URL'), get_required_env('SUPABASE_KEY'))


def seed_diagnostic_question_bank(path: str | Path = DEFAULT_BANK_PATH) -> int:
    records = load_question_bank(path)
    client = create_supabase_client()
    payloads = build_payloads(records)
    client.table('diagnostic_question_bank').upsert(payloads, on_conflict='question_id').execute()
    return len(payloads)


if __name__ == '__main__':
    count = seed_diagnostic_question_bank()
    print(f'Seeded {count} diagnostic anchor questions.')
