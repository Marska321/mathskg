from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from services.diagnostic_engine import select_next_diagnostic_skill
from core.database import supabase as supabase_client

router = APIRouter()

# Pydantic schema for the request body
class DiagnosticRequest(BaseModel):
    student_id: str

@router.post("/diagnostic/next-question")
async def get_next_question(request: DiagnosticRequest):
    """
    Evaluates the student's current mastery state and fetches the most optimal next question.
    """
    try:
        # 1. Fetch all skills to establish the baseline
        skills_response = supabase_client.table("skills").select("skill_id").execute()
        all_skill_ids = [skill['skill_id'] for skill in skills_response.data]
        
        # 2. Fetch the student's current diagnostic state from the StudentSkill table
        # According to the schema, this tracks student_id, skill_id, and status
        state_response = supabase_client.table("student_mastery")\
            .select("skill_id, status")\
            .eq("student_id", request.student_id)\
            .execute()
            
        # Convert the database response into the dictionary our engine expects
        # If a skill isn't in the student's record yet, it defaults to "unknown"
        known_state = {row['skill_id']: row['status'] for row in state_response.data}
        current_state = {skill_id: known_state.get(skill_id, "unknown") for skill_id in all_skill_ids}
        
        # 3. Fetch the graph edges (the dependency structure)
        edges_response = supabase_client.table("skill_prerequisites")\
            .select("skill_id, prerequisite_id")\
            .execute()
            
        edges = edges_response.data
        
        # 4. Ask the engine what the best next skill is based on the weights
        next_skill_id = select_next_diagnostic_skill(current_state, edges)
        
        # If the engine returns None, the sweep has categorized every node!
        if not next_skill_id:
            return {
                "status": "complete", 
                "message": "Diagnostic phase finished. Mastery graph populated."
            }
            
        # 5. Fetch a problem template for the selected skill
        # We query the engine!
        from templates.engine import LumenEngine
        engine = LumenEngine()
        template = engine.generate_practice(next_skill_id)
        
        return {
            "status": "in_progress",
            "next_skill": next_skill_id,
            "template": template
        }
        
    except Exception as e:
        # Catch any database or logic errors and return a clean HTTP 500
        raise HTTPException(status_code=500, detail=str(e))
