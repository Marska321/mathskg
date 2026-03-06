from core.database import supabase

def get_skill_prerequisites(skill_id: str) -> list[str]:
    res = supabase.table("skill_prerequisites").select("prerequisite_id").eq("skill_id", skill_id).execute()
    return [edge['prerequisite_id'] for edge in res.data]

def get_downstream_dependencies(skill_id: str) -> list[str]:
    res = supabase.table("skill_prerequisites").select("skill_id").eq("prerequisite_id", skill_id).execute()
    return [edge['skill_id'] for edge in res.data]
