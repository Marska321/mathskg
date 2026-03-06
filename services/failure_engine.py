def calculate_failure_score(downstream_nodes_count: int, observed_failure_rate: float, skill_difficulty: int) -> float:
    """
    Calculates the structural failure risk of a node.
    """
    # FailureScore = (# of downstream nodes) * (observed failure rate) * (skill difficulty)
    score = downstream_nodes_count * observed_failure_rate * skill_difficulty
    return round(score, 2)

def flag_bottleneck_nodes(supabase_client, failure_threshold: float = 15.0):
    """
    Scans the knowledge graph and updates the failure_risk status of skills.
    """
    # Fetch all skills and their performance metrics (pseudo-query for your DB structure)
    skills = supabase_client.table("skills").select("id, downstream_count, failure_rate, difficulty").execute()
    
    updates = []
    for skill in skills.data:
        score = calculate_failure_score(skill['downstream_count'], skill['failure_rate'], skill['difficulty'])
        
        # Determine risk tier based on score
        if score >= failure_threshold:
            risk = 'high'
        elif score >= (failure_threshold / 2):
            risk = 'medium'
        else:
            risk = 'low'
            
        updates.append({"id": skill['id'], "failure_risk": risk})
        
    # Batch update the Supabase table
    if updates:
        supabase_client.table("skills").upsert(updates).execute()
        
    return f"Processed {len(updates)} nodes for failure risk."