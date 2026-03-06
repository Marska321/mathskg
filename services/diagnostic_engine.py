# diagnostic_engine.py
from typing import Optional

def initialize_diagnostic_state(skill_ids: list[str]) -> dict:
    """
    Sets all skills in the graph to an 'unknown' state at the start of the test.
    """
    return {skill_id: "unknown" for skill_id in skill_ids}

def get_all_prerequisites(skill_id: str, edges: list[dict], visited: set = None) -> set:
    """Recursively fetches all upstream prerequisites for a given skill."""
    if visited is None:
        visited = set()
        
    direct_prereqs = [edge['prerequisite_id'] for edge in edges if edge['skill_id'] == skill_id]
    
    for prereq in direct_prereqs:
        if prereq not in visited:
            visited.add(prereq)
            get_all_prerequisites(prereq, edges, visited)
            
    return visited

def get_all_downstream_dependencies(skill_id: str, edges: list[dict], visited: set = None) -> set:
    """Recursively fetches all downstream skills that rely on a given skill."""
    if visited is None:
        visited = set()
        
    direct_deps = [edge['skill_id'] for edge in edges if edge['prerequisite_id'] == skill_id]
    
    for dep in direct_deps:
        if dep not in visited:
            visited.add(dep)
            get_all_downstream_dependencies(dep, edges, visited)
            
    return visited

def process_diagnostic_answer(
    skill_id: str, 
    is_correct: bool, 
    current_state: dict, 
    edges: list[dict]
) -> dict:
    """
    Updates the diagnostic state based on a single answer.
    """
    updated_state = current_state.copy()
    
    if is_correct:
        # 1. Mark the current skill as mastered
        updated_state[skill_id] = "mastered"
        
        # 2. Upward Sweep: Mark all prerequisites as assumed_mastered
        prereqs = get_all_prerequisites(skill_id, edges)
        for p in prereqs:
            # Only overwrite if we don't already have hard data
            if updated_state[p] == "unknown":
                updated_state[p] = "assumed_mastered"
                
    else:
        # 1. Mark the current skill as gap
        updated_state[skill_id] = "gap"
        
        # 2. Downward Sweep: Mark all dependent skills as assumed_gap
        deps = get_all_downstream_dependencies(skill_id, edges)
        for d in deps:
            if updated_state[d] == "unknown":
                updated_state[d] = "assumed_gap"
                
    return updated_state

def is_diagnostic_complete(current_state: dict, question_count: int, max_questions: int = 30) -> bool:
    """
    Checks if the diagnostic test should terminate.
    """
    # Terminate if we've hit the question limit
    if question_count >= max_questions:
        return True
        
    # Terminate if there are no more 'unknown' nodes
    unknown_count = sum(1 for state in current_state.values() if state == "unknown")
    if unknown_count == 0:
        return True
        
    return False

def calculate_node_weight(skill_id: str, current_state: dict, edges: list[dict]) -> int:
    """
    Calculates how many 'unknown' nodes this skill will resolve in the worst-case scenario.
    """
    # Fetch all connected nodes (using the sweep functions we defined earlier)
    prereqs = get_all_prerequisites(skill_id, edges)
    deps = get_all_downstream_dependencies(skill_id, edges)
    
    # Filter down to only the nodes we don't know the answer to yet
    unknown_prereqs = [p for p in prereqs if current_state.get(p) == "unknown"]
    unknown_deps = [d for d in deps if current_state.get(d) == "unknown"]
    
    # If they pass, we auto-solve `unknown_prereqs`. 
    # If they fail, we auto-solve `unknown_deps`.
    # To optimize the test, we assume the worst case and try to maximize that floor.
    worst_case_elimination = min(len(unknown_prereqs), len(unknown_deps))
    
    return worst_case_elimination

def select_next_diagnostic_skill(current_state: dict, edges: list[dict]) -> Optional[str]:
    """
    Scans all remaining unknown skills and selects the one with the highest information gain.
    """
    # Get a list of everything we haven't tested or assumed yet
    unknown_skills = [skill_id for skill_id, state in current_state.items() if state == "unknown"]
    
    if not unknown_skills:
        return None # The diagnostic is complete
        
    best_skill = None
    max_weight = -1
    
    for skill in unknown_skills:
        weight = calculate_node_weight(skill, current_state, edges)
        
        # We found a node that splits the remaining graph better
        if weight > max_weight:
            max_weight = weight
            best_skill = skill
            
    # Fallback: if we are at the fringes of the graph and weights are 0, 
    # just pick the first available unknown node to keep moving.
    return best_skill if best_skill else unknown_skills[0]