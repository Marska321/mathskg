from models.domain import MasteryStatus


def build_diagnostic_result(current_state: dict[str, str], question_count: int) -> dict:
    total = len(current_state)

    mastered = sorted(
        skill_id
        for skill_id, state in current_state.items()
        if state in (MasteryStatus.MASTERED.value, MasteryStatus.ASSUMED_MASTERED.value)
    )
    gaps = sorted(
        skill_id
        for skill_id, state in current_state.items()
        if state in (MasteryStatus.GAP.value, MasteryStatus.ASSUMED_GAP.value)
    )
    unknown = sorted(
        skill_id
        for skill_id, state in current_state.items()
        if state == MasteryStatus.UNKNOWN.value
    )

    resolved_count = total - len(unknown)
    confidence = round((resolved_count / total), 2) if total else 0.0

    placement_skill_id = None
    rationale = "Insufficient diagnostic evidence to select an entry skill."

    if gaps:
        placement_skill_id = gaps[0]
        rationale = "Detected foundational gaps; begin targeted repair from the earliest unresolved gap."
    elif mastered:
        placement_skill_id = mastered[-1]
        rationale = "No active gaps detected; continue from the highest currently demonstrated skill."

    return {
        "question_count": question_count,
        "skill_count": total,
        "resolved_count": resolved_count,
        "confidence": confidence,
        "mastered_skills": mastered,
        "gap_skills": gaps,
        "unknown_skills": unknown,
        "placement_skill_id": placement_skill_id,
        "rationale": rationale,
    }
