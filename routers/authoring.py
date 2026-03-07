from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from core.database import supabase
from models.authoring import (
    PublishPayload,
    SkillAuthoringPayload,
    SkillUpdatePayload,
    TemplateCreatePayload,
)
from services.authoring_service import (
    AuthoringError,
    build_publish_update,
    ensure_template_exists,
    normalize_skill_create_payload,
    normalize_skill_update_payload,
    validate_publish_transition,
)

router = APIRouter()


@router.get("/authoring/review")
def authoring_console_page():
    page_path = Path(__file__).resolve().parent.parent / "authoring.html"
    if not page_path.exists():
        raise HTTPException(status_code=404, detail="Authoring dashboard file not found.")
    return FileResponse(page_path)


@router.get("/authoring/skills")
def authoring_get_skills(approval_status: str | None = Query(default=None)):
    try:
        query = supabase.table("skills").select("*")
        if approval_status:
            query = query.eq("approval_status", approval_status)
        response = query.execute()
        return {"skills": response.data or []}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/authoring/skills")
def authoring_create_skill(payload: SkillAuthoringPayload):
    try:
        skill_payload = normalize_skill_create_payload(payload.model_dump())
        response = supabase.table("skills").upsert(skill_payload).execute()
        return {"skill": (response.data or [skill_payload])[0]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.put("/authoring/skills/{skill_id}")
def authoring_update_skill(skill_id: str, payload: SkillUpdatePayload):
    try:
        update_payload = normalize_skill_update_payload(payload.model_dump())
        if not update_payload:
            raise HTTPException(status_code=400, detail="No fields provided for update.")

        response = (
            supabase.table("skills")
            .update(update_payload)
            .eq("skill_id", skill_id)
            .execute()
        )
        return {"skill": (response.data or [])}
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/authoring/templates")
def authoring_create_template(payload: TemplateCreatePayload):
    try:
        template_payload = payload.model_dump()
        response = (
            supabase.table("question_templates")
            .upsert(template_payload, on_conflict="template_id")
            .execute()
        )

        (
            supabase.table("skills")
            .update({"question_template": payload.template_id})
            .eq("skill_id", payload.skill_id)
            .execute()
        )

        return {"template": (response.data or [template_payload])[0]}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/authoring/publish")
def authoring_publish(payload: PublishPayload):
    try:
        skill_response = (
            supabase.table("skills")
            .select("skill_id, approval_status")
            .eq("skill_id", payload.skill_id)
            .limit(1)
            .execute()
        )
        if not skill_response.data:
            raise HTTPException(status_code=404, detail="Skill not found.")

        skill_row = skill_response.data[0]
        validate_publish_transition(skill_row.get("approval_status"), force=payload.force)

        template_response = (
            supabase.table("question_templates")
            .select("template_id")
            .eq("skill_id", payload.skill_id)
            .execute()
        )
        ensure_template_exists(template_response.data or [], force=payload.force)

        update_payload = build_publish_update(payload.skill_id)
        update_response = (
            supabase.table("skills")
            .update(update_payload)
            .eq("skill_id", payload.skill_id)
            .execute()
        )

        return {
            "status": "published",
            "skill": (update_response.data or [update_payload])[0],
        }

    except AuthoringError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
