from fastapi import APIRouter, HTTPException, Query

from core.database import supabase
from services.teacher_analytics import (
    build_teacher_bottlenecks_response,
    build_teacher_caps_coverage_response,
    build_teacher_heatmap_response,
)

router = APIRouter()


def _fetch_class_student_ids(class_id: str) -> list[str]:
    student_ids: set[str] = set()

    # Preferred mapping table.
    try:
        mapping = (
            supabase.table("class_students")
            .select("student_id")
            .eq("class_id", class_id)
            .execute()
        )
        for row in mapping.data or []:
            student_id = row.get("student_id")
            if student_id:
                student_ids.add(student_id)
    except Exception:
        pass

    # Fallback: class_id stored directly on students table.
    try:
        students = (
            supabase.table("students")
            .select("id")
            .eq("class_id", class_id)
            .execute()
        )
        for row in students.data or []:
            student_id = row.get("id")
            if student_id:
                student_ids.add(student_id)
    except Exception:
        pass

    return sorted(student_ids)


def _fetch_class_mastery_rows(student_ids: list[str]) -> list[dict]:
    rows: list[dict] = []
    if not student_ids:
        return rows

    for student_id in student_ids:
        response = (
            supabase.table("student_mastery")
            .select("student_id, skill_id, status, active_repair_path")
            .eq("student_id", student_id)
            .execute()
        )
        rows.extend(response.data or [])

    return rows


def _fetch_class_attempt_rows(student_ids: list[str]) -> list[dict]:
    rows: list[dict] = []
    if not student_ids:
        return rows

    for student_id in student_ids:
        response = (
            supabase.table("attempt_logs")
            .select("student_id, skill_id, is_correct, error_type_detected")
            .eq("student_id", student_id)
            .execute()
        )
        rows.extend(response.data or [])

    return rows


@router.get("/teacher/class/{class_id}/heatmap")
def get_teacher_heatmap(class_id: str):
    try:
        student_ids = _fetch_class_student_ids(class_id)
        mastery_rows = _fetch_class_mastery_rows(student_ids)
        payload = build_teacher_heatmap_response(class_id, student_ids, mastery_rows)
        return payload.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/teacher/class/{class_id}/bottlenecks")
def get_teacher_bottlenecks(class_id: str, min_attempts: int = Query(default=2, ge=1)):
    try:
        student_ids = _fetch_class_student_ids(class_id)
        attempts = _fetch_class_attempt_rows(student_ids)
        payload = build_teacher_bottlenecks_response(
            class_id,
            student_ids,
            attempts,
            min_attempts=min_attempts,
        )
        return payload.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/teacher/class/{class_id}/caps-coverage")
def get_teacher_caps_coverage(class_id: str):
    try:
        student_ids = _fetch_class_student_ids(class_id)
        mastery_rows = _fetch_class_mastery_rows(student_ids)
        skills_rows_response = supabase.table("skills").select("skill_id, caps_reference").execute()
        payload = build_teacher_caps_coverage_response(
            class_id,
            student_ids,
            mastery_rows,
            skills_rows_response.data or [],
        )
        return payload.model_dump()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
