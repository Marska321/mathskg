from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from core.database import supabase
from templates.engine import LumenEngine
from services.failure_engine import flag_bottleneck_nodes

router = APIRouter()
engine = LumenEngine()

@router.get("/")
def read_root():
    return {"message": "Welcome to the Lumen Engine API"}

@router.get("/review", response_class=HTMLResponse)
def serve_review_dashboard():
    return "<html><body><h1>Lumen Dashboard</h1></body></html>"
    
@router.get("/api/admin/pending-templates")
def get_pending_templates():
    res = supabase.table("skills").select("skill_id, skill_name").eq("approval_status", "pending").execute()
    return {"pending_skills": res.data}

@router.get("/api/admin/preview-template/{skill_id}")
def get_template_previews(skill_id: str):
    try:
        ex1 = engine.generate_practice(skill_id)
        ex2 = engine.generate_practice(skill_id)
        ex3 = engine.generate_practice(skill_id)
        return {"skill_id": skill_id, "examples": [ex1, ex2, ex3]}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/api/admin/approve-template/{skill_id}")
def approve_template(skill_id: str):
    supabase.table("skills").update({"approval_status": "live"}).eq("skill_id", skill_id).execute()
    return {"message": f"Skill {skill_id} gracefully approved!"}

@router.post("/api/admin/recalculate-failure-scores")
def update_failure_scores():
    flag_bottleneck_nodes(supabase)
    return {"message": "Failure scores updated."}
