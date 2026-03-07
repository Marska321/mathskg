from fastapi import APIRouter

from core.database import supabase
from models.domain import MasteryStatus
from models.mastery import PracticeRequest
from models.submission import AnswerSubmission
from services.adaptive_policy import decide_next_skill_policy, prioritize_repair_nodes
from services.attempt_evaluator import evaluate_attempt
from services.graph_service import get_skill_prerequisites
from services.mastery_engine import update_student_mastery
from templates.engine import LumenEngine

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
        "question": payload,
    }


@router.post("/generate-practice")
def generate_practice(request: PracticeRequest):
    return generate_question_payload(request.student_id, request.skill_id)


@router.get("/next-skill")
def get_next_skill(student_id: str):
    mastery_rows_response = (
        supabase.table("student_mastery")
        .select("skill_id, status, active_repair_path")
        .eq("student_id", student_id)
        .execute()
    )
    mastery_rows = mastery_rows_response.data or []

    edges_response = supabase.table("skill_prerequisites").select("skill_id, prerequisite_id").execute()
    edges = edges_response.data or []

    decision = decide_next_skill_policy(mastery_rows, edges)
    target_skill_id = decision["target_skill_id"]

    if decision["policy"] == "complete" or target_skill_id is None:
        return {
            "policy": decision["policy"],
            "reason": decision["reason"],
            "message": "You have mastered the entire mathematical universe!",
        }

    if decision["policy"] == "new":
        (
            supabase.table("student_mastery")
            .upsert(
                {
                    "student_id": student_id,
                    "skill_id": target_skill_id,
                    "status": MasteryStatus.LEARNING.value,
                }
            )
            .execute()
        )

    payload = generate_question_payload(student_id, target_skill_id)
    return {
        "policy": decision["policy"],
        "reason": decision["reason"],
        "source_skill_id": decision["source_skill_id"],
        **payload,
    }


@router.post("/submit-answer")
def submit_answer(submission: AnswerSubmission):
    attempt_result = evaluate_attempt(
        student_answer=submission.student_answer,
        correct_answer=submission.correct_answer,
        error_mapping=submission.error_mapping,
    )
    is_correct = attempt_result["is_correct"]
    error_type = attempt_result["error_type"]

    (
        supabase.table("attempt_logs")
        .insert(
            {
                "student_id": submission.student_id,
                "skill_id": submission.skill_id,
                "is_correct": is_correct,
                "time_taken_seconds": submission.time_taken_seconds,
                "error_type_detected": error_type,
            }
        )
        .execute()
    )

    new_status = update_student_mastery(
        submission.student_id,
        submission.skill_id,
        is_correct,
        error_type,
    )

    message = ""
    if new_status == MasteryStatus.MASTERED.value:
        message = "Skill MASTERED! You're ready to move on."
    elif new_status == MasteryStatus.LEARNING.value and not is_correct:
        if error_type and error_type != "UNKNOWN_ERROR":
            message = f"Oops! I think you might have made this mistake: {error_type}. Check the hints!"
        else:
            message = "Incorrect. Review the hints and try again!"
    elif new_status == MasteryStatus.LEARNING.value and is_correct:
        message = "Good job! Keep going to prove your mastery."

    if new_status == MasteryStatus.NEEDS_REVIEW.value:
        repair_nodes = get_skill_prerequisites(submission.skill_id)
        repair_nodes = prioritize_repair_nodes(repair_nodes, error_type)
        if repair_nodes:
            (
                supabase.table("student_mastery")
                .update(
                    {
                        "status": MasteryStatus.NEEDS_REVIEW.value,
                        "active_repair_path": repair_nodes,
                    }
                )
                .eq("student_id", submission.student_id)
                .eq("skill_id", submission.skill_id)
                .execute()
            )

            message = f"Mastery threshold not met. Rerouting to foundational prerequisite: {repair_nodes[0]}"
        else:
            message = "Let's pause. We will review the fundamentals and come back!"

    return {
        "status": "success",
        "is_correct": is_correct,
        "mastery_status": new_status,
        "message": message,
    }
