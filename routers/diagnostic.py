from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from core.database import supabase as supabase_client
from models.domain import MasteryStatus
from services.diagnostic_engine import (
    initialize_diagnostic_state,
    is_diagnostic_complete,
    process_diagnostic_answer,
    select_next_diagnostic_skill,
)
from services.diagnostic_result import build_diagnostic_result
from services.diagnostic_session_store import (
    create_diagnostic_session,
    get_diagnostic_session,
    update_diagnostic_session,
)
from templates.engine import LumenEngine

router = APIRouter()
engine = LumenEngine()


class DiagnosticStartRequest(BaseModel):
    student_id: str


class DiagnosticAnswerRequest(BaseModel):
    session_id: str
    skill_id: str
    is_correct: bool


def _normalize_status(raw_value: str | None) -> str:
    if raw_value is None:
        return MasteryStatus.UNKNOWN.value
    try:
        return MasteryStatus(raw_value).value
    except ValueError:
        return MasteryStatus.UNKNOWN.value


def _get_all_skill_ids() -> list[str]:
    response = supabase_client.table("skills").select("skill_id").execute()
    return [skill["skill_id"] for skill in response.data]


def _get_edges() -> list[dict[str, str]]:
    response = (
        supabase_client.table("skill_prerequisites")
        .select("skill_id, prerequisite_id")
        .execute()
    )
    return response.data


def _select_next_templated_skill(current_state: dict[str, str], edges: list[dict[str, str]]) -> str | None:
    templated_skills = set(engine.registry.keys())
    templated_state = {
        skill_id: state
        for skill_id, state in current_state.items()
        if skill_id in templated_skills
    }
    if not templated_state:
        return None
    return select_next_diagnostic_skill(templated_state, edges)


def _template_payload(skill_id: str) -> dict:
    try:
        return engine.generate_practice(skill_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def _load_student_state(student_id: str, all_skill_ids: list[str]) -> dict[str, str]:
    state_response = (
        supabase_client.table("student_mastery")
        .select("skill_id, status")
        .eq("student_id", student_id)
        .execute()
    )
    known_state = {
        row["skill_id"]: _normalize_status(row.get("status"))
        for row in state_response.data
    }
    return {
        skill_id: known_state.get(skill_id, MasteryStatus.UNKNOWN.value)
        for skill_id in all_skill_ids
    }


@router.post("/diagnostic/start")
async def diagnostic_start(request: DiagnosticStartRequest):
    try:
        all_skill_ids = _get_all_skill_ids()
        if not all_skill_ids:
            raise HTTPException(status_code=404, detail="No skills found for diagnostic.")

        initial_state = initialize_diagnostic_state(all_skill_ids)
        student_state = _load_student_state(request.student_id, all_skill_ids)

        # Prefer existing mastery evidence over blank diagnostic initialization.
        current_state = {
            skill_id: student_state.get(skill_id, initial_state[skill_id])
            for skill_id in all_skill_ids
        }

        edges = _get_edges()
        next_skill_id = _select_next_templated_skill(current_state, edges)
        if not next_skill_id:
            raise HTTPException(
                status_code=409,
                detail="No diagnostic templates are currently available for the configured skills.",
            )

        session = create_diagnostic_session(request.student_id, current_state)
        session = update_diagnostic_session(
            session["session_id"],
            {"next_skill_id": next_skill_id},
        )
        if session is None:
            raise HTTPException(status_code=500, detail="Failed to create diagnostic session.")

        return {
            "status": "in_progress",
            "session_id": session["session_id"],
            "next_skill": next_skill_id,
            "question_count": session["question_count"],
            "template": _template_payload(next_skill_id),
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/diagnostic/answer")
async def diagnostic_answer(request: DiagnosticAnswerRequest):
    try:
        session = get_diagnostic_session(request.session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Diagnostic session not found.")

        if session.get("status") == "complete":
            result = build_diagnostic_result(
                session.get("current_state") or {},
                session.get("question_count") or 0,
            )
            return {
                "status": "complete",
                "session_id": session["session_id"],
                **result,
            }

        current_state = session.get("current_state") or {}
        edges = _get_edges()
        updated_state = process_diagnostic_answer(
            request.skill_id,
            request.is_correct,
            current_state,
            edges,
        )

        question_count = (session.get("question_count") or 0) + 1
        asked_skills = [*(session.get("asked_skills") or []), request.skill_id]

        complete = is_diagnostic_complete(updated_state, question_count)
        if complete:
            result = build_diagnostic_result(updated_state, question_count)
            saved = update_diagnostic_session(
                session["session_id"],
                {
                    "status": "complete",
                    "current_state": updated_state,
                    "question_count": question_count,
                    "asked_skills": asked_skills,
                    "placement_skill_id": result["placement_skill_id"],
                    "confidence": result["confidence"],
                    "next_skill_id": None,
                },
            )
            if saved is None:
                raise HTTPException(status_code=500, detail="Failed to update diagnostic session.")

            return {
                "status": "complete",
                "session_id": session["session_id"],
                **result,
            }

        next_skill_id = _select_next_templated_skill(updated_state, edges)
        if next_skill_id is None:
            result = build_diagnostic_result(updated_state, question_count)
            saved = update_diagnostic_session(
                session["session_id"],
                {
                    "status": "complete",
                    "current_state": updated_state,
                    "question_count": question_count,
                    "asked_skills": asked_skills,
                    "placement_skill_id": result["placement_skill_id"],
                    "confidence": result["confidence"],
                    "next_skill_id": None,
                },
            )
            if saved is None:
                raise HTTPException(status_code=500, detail="Failed to update diagnostic session.")

            return {
                "status": "complete",
                "session_id": session["session_id"],
                "message": "Diagnostic ended because no templated diagnostic questions remain.",
                **result,
            }

        saved = update_diagnostic_session(
            session["session_id"],
            {
                "status": "in_progress",
                "current_state": updated_state,
                "question_count": question_count,
                "asked_skills": asked_skills,
                "next_skill_id": next_skill_id,
            },
        )
        if saved is None:
            raise HTTPException(status_code=500, detail="Failed to update diagnostic session.")

        return {
            "status": "in_progress",
            "session_id": session["session_id"],
            "next_skill": next_skill_id,
            "question_count": question_count,
            "template": _template_payload(next_skill_id),
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/diagnostic/result")
async def diagnostic_result(session_id: str = Query(..., description="Diagnostic session id")):
    try:
        session = get_diagnostic_session(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="Diagnostic session not found.")

        result = build_diagnostic_result(
            session.get("current_state") or {},
            session.get("question_count") or 0,
        )

        # Persist computed placement for in-progress sessions if not already set.
        if session.get("placement_skill_id") is None and result["placement_skill_id"] is not None:
            update_diagnostic_session(
                session["session_id"],
                {
                    "placement_skill_id": result["placement_skill_id"],
                    "confidence": result["confidence"],
                },
            )

        return {
            "status": session.get("status", "in_progress"),
            "session_id": session["session_id"],
            "student_id": session["student_id"],
            "next_skill": session.get("next_skill_id"),
            **result,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/diagnostic/next-question")
async def get_next_question(request: DiagnosticStartRequest):
    """Backward-compatible alias for diagnostic start."""
    return await diagnostic_start(request)
