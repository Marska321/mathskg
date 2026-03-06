from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.database import supabase as supabase_client
from models.domain import MasteryStatus
from services.diagnostic_engine import select_next_diagnostic_skill

router = APIRouter()


class DiagnosticRequest(BaseModel):
    student_id: str


def _normalize_status(raw_value: str | None) -> str:
    if raw_value is None:
        return MasteryStatus.UNKNOWN.value
    try:
        return MasteryStatus(raw_value).value
    except ValueError:
        return MasteryStatus.UNKNOWN.value


@router.post("/diagnostic/next-question")
async def get_next_question(request: DiagnosticRequest):
    """Evaluates current mastery state and fetches the best next diagnostic question."""
    try:
        skills_response = supabase_client.table("skills").select("skill_id").execute()
        all_skill_ids = [skill["skill_id"] for skill in skills_response.data]

        state_response = (
            supabase_client.table("student_mastery")
            .select("skill_id, status")
            .eq("student_id", request.student_id)
            .execute()
        )

        known_state = {
            row["skill_id"]: _normalize_status(row.get("status"))
            for row in state_response.data
        }
        current_state = {
            skill_id: known_state.get(skill_id, MasteryStatus.UNKNOWN.value)
            for skill_id in all_skill_ids
        }

        edges_response = (
            supabase_client.table("skill_prerequisites")
            .select("skill_id, prerequisite_id")
            .execute()
        )
        edges = edges_response.data

        next_skill_id = select_next_diagnostic_skill(current_state, edges)

        if not next_skill_id:
            return {
                "status": "complete",
                "message": "Diagnostic phase finished. Mastery graph populated.",
            }

        from templates.engine import LumenEngine

        engine = LumenEngine()
        template = engine.generate_practice(next_skill_id)

        return {
            "status": "in_progress",
            "next_skill": next_skill_id,
            "template": template,
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
