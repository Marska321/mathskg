import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.database import get_supabase


supabase = get_supabase()

# 1. The Grade 1-3 Core Foundation Nodes
foundation_skills = [
    {"skill_id": "M1-C-001", "skill_name": "Count forward to 20", "strand": "Number Sense", "caps_reference": "Grade 1 Term 1", "difficulty": 1.1, "failure_risk": "MEDIUM", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M1-C-007", "skill_name": "Skip count by 2, 5, 10", "strand": "Number Sense", "caps_reference": "Grade 1 Term 2", "difficulty": 1.3, "failure_risk": "LOW", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M1-NB-024", "skill_name": "Number bonds to 10", "strand": "Number Sense", "caps_reference": "Grade 1 Term 2", "difficulty": 1.5, "failure_risk": "HIGH", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M2-NB-026", "skill_name": "Number bonds to 20", "strand": "Number Sense", "caps_reference": "Grade 2 Term 1", "difficulty": 2.1, "failure_risk": "HIGH", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M2-PV-040", "skill_name": "Identify tens and ones", "strand": "Place Value", "caps_reference": "Grade 2 Term 1", "difficulty": 2.2, "failure_risk": "HIGH", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M2-PV-042", "skill_name": "Write numbers in expanded form", "strand": "Place Value", "caps_reference": "Grade 2 Term 2", "difficulty": 2.3, "failure_risk": "HIGH", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M2-A-045", "skill_name": "Add 2-digit numbers without carrying", "strand": "Addition", "caps_reference": "Grade 2 Term 2", "difficulty": 2.4, "failure_risk": "MEDIUM", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M2-A-048", "skill_name": "Add 2-digit numbers with carrying", "strand": "Addition", "caps_reference": "Grade 2 Term 3", "difficulty": 2.8, "failure_risk": "HIGH", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M2-S-049", "skill_name": "Subtract 2-digit numbers without borrowing", "strand": "Subtraction", "caps_reference": "Grade 2 Term 2", "difficulty": 2.4, "failure_risk": "MEDIUM", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M3-S-052", "skill_name": "Subtract with borrowing", "strand": "Subtraction", "caps_reference": "Grade 3 Term 1", "difficulty": 3.2, "failure_risk": "HIGH", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M3-M-055", "skill_name": "Repeated addition", "strand": "Multiplication", "caps_reference": "Grade 3 Term 1", "difficulty": 3.0, "failure_risk": "MEDIUM", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
    {"skill_id": "M3-M-056", "skill_name": "Multiplication as arrays", "strand": "Multiplication", "caps_reference": "Grade 3 Term 1", "difficulty": 3.1, "failure_risk": "MEDIUM", "approval_status": "live", "mastery_criteria": {"accuracy": 0.8, "speed": 15}},
]

foundation_edges = [
    {"skill_id": "M1-NB-024", "prerequisite_id": "M1-C-001"},
    {"skill_id": "M2-NB-026", "prerequisite_id": "M1-NB-024"},
    {"skill_id": "M2-PV-040", "prerequisite_id": "M1-C-001"},
    {"skill_id": "M2-PV-042", "prerequisite_id": "M2-PV-040"},
    {"skill_id": "M2-A-045", "prerequisite_id": "M2-PV-040"},
    {"skill_id": "M2-A-048", "prerequisite_id": "M2-A-045"},
    {"skill_id": "M2-A-048", "prerequisite_id": "M1-NB-024"},
    {"skill_id": "M2-S-049", "prerequisite_id": "M2-PV-040"},
    {"skill_id": "M3-S-052", "prerequisite_id": "M2-S-049"},
    {"skill_id": "M3-S-052", "prerequisite_id": "M2-PV-042"},
    {"skill_id": "M3-M-055", "prerequisite_id": "M1-C-007"},
    {"skill_id": "M3-M-056", "prerequisite_id": "M3-M-055"},
]


def seed_database() -> None:
    print("Injecting Grade 1-3 Foundation Nodes...")
    for skill in foundation_skills:
        try:
            supabase.table("skills").upsert(skill).execute()
            print(f"  Added: {skill['skill_id']} - {skill['skill_name']}")
        except Exception as exc:
            print(f"  Error on {skill['skill_id']}: {exc}")

    print("\nWiring Dependency Edges...")
    for edge in foundation_edges:
        try:
            supabase.table("skill_prerequisites").upsert(
                {
                    "skill_id": edge["skill_id"],
                    "prerequisite_id": edge["prerequisite_id"],
                }
            ).execute()
            print(f"  Linked: {edge['prerequisite_id']} -> {edge['skill_id']}")
        except Exception as exc:
            print(f"  Error linking {edge['skill_id']}: {exc}")

    print("\nFoundation Knowledge Graph Successfully Built.")


if __name__ == "__main__":
    seed_database()
