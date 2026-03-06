from fastapi import APIRouter
from models.mastery import PracticeRequest
from models.submission import AnswerSubmission
from core.database import supabase
from templates.engine import LumenEngine
from services.mastery_engine import update_student_mastery
from services.graph_service import get_skill_prerequisites

router = APIRouter()
engine = LumenEngine()

def generate_question_payload(student_id: str, skill_id: str):
    skill_data = supabase.table("skills").select("*").eq("skill_id", skill_id).execute()
    if not skill_data.data:
        return {"error": "Skill not found"}
        
    payload = engine.generate_practice(skill_id)
    return {
        "student_id": student_id,
        "skill": skill_data.data[0],
        "question": payload
    }

@router.post("/generate-practice")
def generate_practice(request: PracticeRequest):
    return generate_question_payload(request.student_id, request.skill_id)

@router.get("/next-skill")
def get_next_skill(student_id: str):
    res = supabase.table("student_mastery").select("skill_id, status, active_repair_path").eq("student_id", student_id).execute()
    
    learning_skills = [s for s in res.data if s["status"] in ["learning", "needs_review"]]
    if learning_skills:
        target = learning_skills[0]
        if target.get("active_repair_path") and len(target["active_repair_path"]) > 0:
            return generate_question_payload(student_id, target["active_repair_path"][0])
        return generate_question_payload(student_id, target["skill_id"])
        
    mastered_skills = [s["skill_id"] for s in res.data if s["status"] == "mastered"]
    
    all_edges = supabase.table("skill_prerequisites").select("*").execute()
    available_skills = set()
    
    for edge in all_edges.data:
        if edge["prerequisite_id"] in mastered_skills:
            deps = supabase.table("skill_prerequisites").select("prerequisite_id").eq("skill_id", edge["skill_id"]).execute()
            if all(d["prerequisite_id"] in mastered_skills for d in deps.data):
                available_skills.add(edge["skill_id"])
                
    available_skills = available_skills - set(mastered_skills)
    
    if available_skills:
        next_skill = list(available_skills)[0]
        supabase.table("student_mastery").upsert({
            "student_id": student_id,
            "skill_id": next_skill,
            "status": "learning"
        }).execute()
        return generate_question_payload(student_id, next_skill)
        
    return {"message": "You have mastered the entire mathematical universe!"}

@router.post("/submit-answer")
def submit_answer(submission: AnswerSubmission):
    is_correct = submission.student_answer.strip().lower() == submission.correct_answer.strip().lower()
    
    error_type = None
    if not is_correct:
        error_type = submission.error_mapping.get(submission.student_answer, "UNKNOWN_ERROR")
        
    supabase.table("attempt_logs").insert({
        "student_id": submission.student_id,
        "skill_id": submission.skill_id,
        "is_correct": is_correct,
        "time_taken_seconds": submission.time_taken_seconds,
        "error_type_detected": error_type
    }).execute()
    
    new_status = update_student_mastery(submission.student_id, submission.skill_id, is_correct, error_type)
    
    message = ""
    if new_status == "mastered":
        message = "Skill MASTERED! You're ready to move on."
    elif new_status == "learning" and not is_correct:
        if error_type and error_type != "UNKNOWN_ERROR":
            message = f"Oops! I think you might have made this mistake: {error_type}. Check the hints!"
        else:
            message = "Incorrect. Review the hints and try again!"
    elif new_status == "learning" and is_correct:
        message = "Good job! Keep going to prove your mastery."
        
    if new_status == "needs_review":
        repair_nodes = get_skill_prerequisites(submission.skill_id)
        if repair_nodes:
            if error_type == "MC_SUB_02_TENS_COLUMN_ERROR" and "M2-PV-040" in repair_nodes:
                repair_nodes.remove("M2-PV-040")
                repair_nodes.insert(0, "M2-PV-040") 
            elif error_type == "MC_SUB_01_ADDED_INSTEAD" and "M2-S-049" in repair_nodes:
                repair_nodes.remove("M2-S-049")
                repair_nodes.insert(0, "M2-S-049")
                
            supabase.table("student_mastery").update({
                "status": "needs_review",
                "active_repair_path": repair_nodes
            }).eq("student_id", submission.student_id).eq("skill_id", submission.skill_id).execute()
            
            message = f"Mastery threshold not met. Rerouting to foundational prerequisite: {repair_nodes[0]}"
        else:
            message = "Let's pause. We will review the fundamentals and come back!"
            
    return {
        "status": "success",
        "is_correct": is_correct,
        "mastery_status": new_status,
        "message": message
    }
