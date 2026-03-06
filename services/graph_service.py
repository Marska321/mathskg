from collections import defaultdict

from core.database import supabase


def _fetch_edges() -> list[dict[str, str]]:
    response = supabase.table("skill_prerequisites").select("skill_id, prerequisite_id").execute()
    return response.data or []


def _build_adjacency(edges: list[dict[str, str]]) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    prereqs_by_skill: dict[str, set[str]] = defaultdict(set)
    downstream_by_prereq: dict[str, set[str]] = defaultdict(set)

    for edge in edges:
        skill_id = edge["skill_id"]
        prereq_id = edge["prerequisite_id"]
        prereqs_by_skill[skill_id].add(prereq_id)
        downstream_by_prereq[prereq_id].add(skill_id)

    return prereqs_by_skill, downstream_by_prereq


def _traverse(start_skill_id: str, adjacency: dict[str, set[str]]) -> list[str]:
    visited: set[str] = set()
    stack = sorted(adjacency.get(start_skill_id, set()), reverse=True)

    while stack:
        node = stack.pop()
        if node in visited:
            continue
        visited.add(node)

        for neighbor in sorted(adjacency.get(node, set()), reverse=True):
            if neighbor not in visited:
                stack.append(neighbor)

    return sorted(visited)


def get_skill_prerequisites(skill_id: str) -> list[str]:
    edges = _fetch_edges()
    prereqs_by_skill, _ = _build_adjacency(edges)
    return sorted(prereqs_by_skill.get(skill_id, set()))


def get_downstream_dependencies(skill_id: str) -> list[str]:
    edges = _fetch_edges()
    _, downstream_by_prereq = _build_adjacency(edges)
    return sorted(downstream_by_prereq.get(skill_id, set()))


def get_all_prerequisites(skill_id: str) -> list[str]:
    edges = _fetch_edges()
    prereqs_by_skill, _ = _build_adjacency(edges)
    return _traverse(skill_id, prereqs_by_skill)


def get_all_downstream_dependencies(skill_id: str) -> list[str]:
    edges = _fetch_edges()
    _, downstream_by_prereq = _build_adjacency(edges)
    return _traverse(skill_id, downstream_by_prereq)
