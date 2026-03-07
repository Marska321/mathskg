from fastapi import APIRouter, HTTPException, Query

from core.database import supabase
from services.student_reports import (
    build_mastery_response,
    build_repair_path_response,
    build_student_report_response,
)

router = APIRouter()


@router.get("/students/{student_id}/mastery")
def get_student_mastery(student_id: str):
    try:
        response = (
            supabase.table("student_mastery")
            .select("skill_id, status, current_streak, error_patterns, active_repair_path")
            .eq("student_id", student_id)
            .execute()
        )
        payload = build_mastery_response(student_id, response.data or [])
        return payload.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/students/{student_id}/repair-path")
def get_student_repair_path(student_id: str, skill_id: str | None = Query(default=None)):
    try:
        response = (
            supabase.table("student_mastery")
            .select("skill_id, status, active_repair_path")
            .eq("student_id", student_id)
            .execute()
        )
        payload = build_repair_path_response(student_id, response.data or [], skill_id=skill_id)
        return payload.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/students/{student_id}/report")
def get_student_report(student_id: str):
    try:
        mastery_response = (
            supabase.table("student_mastery")
            .select("skill_id, status, current_streak, error_patterns, active_repair_path")
            .eq("student_id", student_id)
            .execute()
        )
        attempts_response = (
            supabase.table("attempt_logs")
            .select("is_correct, error_type_detected")
            .eq("student_id", student_id)
            .execute()
        )

        payload = build_student_report_response(
            student_id,
            mastery_rows=mastery_response.data or [],
            attempts=attempts_response.data or [],
        )
        return payload.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
