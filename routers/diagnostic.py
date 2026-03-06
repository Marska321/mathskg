from fastapi import APIRouter
from services.diagnostic_engine import select_next_diagnostic_skill

router = APIRouter()

@router.post("/diagnostic/next-question")
async def get_next_question(student_id: str):
    # Ask the engine what the best next skill is
    current_state = {}
    edges = []
    template = {}
    next_skill_id = select_next_diagnostic_skill(current_state, edges)
    
    if not next_skill_id:
        return {"status": "complete", "message": "Diagnostic finished."}
        
    return {
        "status": "in_progress",
        "next_skill": next_skill_id,
        "template": template
    }
