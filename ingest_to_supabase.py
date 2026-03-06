import json
import os
from supabase import create_client, Client

# 1. Your Supabase Credentials (replace these with your actual project details)
SUPABASE_URL = "https://dbeymbofoledmubfyzmz.supabase.co"
SUPABASE_KEY = "sb_publishable_Ft9zN_KPc2LDVbGKcWj_HA_4kOYErKY"

# Initialize the client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def ingest_graph():
    # 2. Load the local Knowledge Graph
    try:
        with open('caps_graph.json', 'r') as f:
            skills_data = json.load(f)
    except FileNotFoundError:
        print("Error: 'caps_graph.json' not found. Please ensure it is in the same folder.")
        return

    print(f"Found {len(skills_data)} skills. Starting database ingestion...\n")

    prereq_payloads = []

    # 3. Loop through and ingest the Nodes (Skills)
    for skill in skills_data:
        # Format the data to match our SQL schema exactly
        skill_payload = {
            "skill_id": skill["skill_id"],
            "skill_name": skill["skill_name"],
            "caps_reference": skill.get("caps_reference", ""),
            "difficulty": skill.get("difficulty", 1.0),
            "mastery_criteria": skill.get("mastery_criteria", "3 correct in a row"),
            "question_template": skill.get("question_template", "")
        }
        
        # .upsert() ensures we update existing records rather than duplicating them
        supabase.table("skills").upsert(skill_payload).execute()
        print(f"✅ Inserted Node: {skill['skill_id']}")

        # Queue up the prerequisites for the next step
        for prereq_id in skill.get("prerequisites", []):
            prereq_payloads.append({
                "skill_id": skill["skill_id"],
                "prerequisite_id": prereq_id
            })

    print("\nAll nodes ingested successfully. Now building the edges (prerequisites)...\n")

    # 4. Ingest the Edges (Prerequisites)
    # We do this after all skills are loaded to avoid Foreign Key constraint errors
    if prereq_payloads:
        # Upsert the edges. If the edge already exists, it ignores it.
        supabase.table("skill_prerequisites").upsert(
            prereq_payloads, 
            on_conflict="skill_id,prerequisite_id"
        ).execute()
        
    print(f"✅ Inserted {len(prereq_payloads)} prerequisite connections.")
    print("\n🚀 Lumen Knowledge Graph is now live in Supabase!")

if __name__ == "__main__":
    ingest_graph()