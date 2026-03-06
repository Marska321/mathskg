import json
import os

from pydantic import ValidationError
from supabase import Client, create_client

from models.domain import GraphSkillRecord


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            "Set it in your environment or .env file before running this script."
        )
    return value


def _load_and_validate_graph(path: str) -> list[GraphSkillRecord]:
    try:
        with open(path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"'{path}' not found.") from exc

    validation_errors: list[str] = []
    validated_records: list[GraphSkillRecord] = []

    for index, raw_skill in enumerate(raw_data):
        try:
            validated_records.append(GraphSkillRecord.model_validate(raw_skill))
        except ValidationError as exc:
            validation_errors.append(f"record[{index}] skill_id={raw_skill.get('skill_id')}: {exc}")

    if validation_errors:
        details = "\n".join(validation_errors[:20])
        raise ValueError(
            "caps_graph.json validation failed. Fix the following records before ingestion:\n"
            f"{details}"
        )

    return validated_records


supabase: Client = create_client(_required_env("SUPABASE_URL"), _required_env("SUPABASE_KEY"))


def ingest_graph() -> None:
    skills_data = _load_and_validate_graph("caps_graph.json")
    print(f"Found {len(skills_data)} valid skills. Starting database ingestion...\n")

    prereq_payloads: list[dict[str, str]] = []

    for skill in skills_data:
        skill_payload = {
            "skill_id": skill.skill_id,
            "skill_name": skill.skill_name,
            "caps_reference": skill.caps_reference or "",
            "difficulty": skill.difficulty,
            "mastery_criteria": skill.mastery_criteria or "3 correct in a row",
            "question_template": skill.question_template,
        }

        supabase.table("skills").upsert(skill_payload).execute()
        print(f"Inserted Node: {skill.skill_id}")

        for prereq_id in skill.prerequisites:
            prereq_payloads.append(
                {
                    "skill_id": skill.skill_id,
                    "prerequisite_id": prereq_id,
                }
            )

    print("\nAll nodes ingested successfully. Now building the edges (prerequisites)...\n")

    if prereq_payloads:
        supabase.table("skill_prerequisites").upsert(
            prereq_payloads,
            on_conflict="skill_id,prerequisite_id",
        ).execute()

    print(f"Inserted {len(prereq_payloads)} prerequisite connections.")
    print("Lumen Knowledge Graph is now live in Supabase.")


if __name__ == "__main__":
    ingest_graph()
