from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional


class DiagnosticGraph:
    def __init__(
        self,
        graph_path: str = 'caps_graph.json',
        records: Optional[Iterable[dict[str, Any]]] = None,
    ) -> None:
        if records is None:
            records = self._load_records(graph_path)

        self.skills_by_id: dict[str, dict[str, Any]] = {}
        self.prerequisites_by_skill: dict[str, tuple[str, ...]] = {}
        self.dependents_by_skill: dict[str, tuple[str, ...]] = {}
        self.difficulty_by_skill: dict[str, float] = {}
        self.terminal_skill_ids: tuple[str, ...] = ()
        self.tested_skill_ids: set[str] = set()
        self.assumed_known_skill_ids: set[str] = set()

        self._build_indexes(list(records))

    @classmethod
    def from_records(cls, records: Iterable[dict[str, Any]]) -> 'DiagnosticGraph':
        return cls(records=list(records))

    @classmethod
    def from_edges(
        cls,
        edges: list[dict[str, str]],
        skill_ids: Optional[Iterable[str]] = None,
        difficulty_by_skill: Optional[dict[str, float]] = None,
    ) -> 'DiagnosticGraph':
        skill_set = set(skill_ids or [])
        prerequisites_by_skill: dict[str, list[str]] = {}

        for edge in edges:
            skill_id = edge['skill_id']
            prerequisite_id = edge['prerequisite_id']
            skill_set.add(skill_id)
            skill_set.add(prerequisite_id)
            prerequisites_by_skill.setdefault(skill_id, []).append(prerequisite_id)

        records: list[dict[str, Any]] = []
        for skill_id in sorted(skill_set):
            raw_prerequisites = prerequisites_by_skill.get(skill_id, [])
            unique_prerequisites = list(dict.fromkeys(raw_prerequisites))
            records.append(
                {
                    'skill_id': skill_id,
                    'skill_name': skill_id,
                    'prerequisites': unique_prerequisites,
                    'difficulty': (difficulty_by_skill or {}).get(skill_id, 0.0),
                }
            )

        return cls(records=records)

    def get_starting_nodes(self) -> list[str]:
        if self.terminal_skill_ids:
            return list(self.terminal_skill_ids)

        if not self.skills_by_id:
            return []

        highest_difficulty = max(self.difficulty_by_skill.values(), default=0.0)
        fallback = [
            skill_id
            for skill_id, difficulty in self.difficulty_by_skill.items()
            if difficulty == highest_difficulty
        ]
        return self._sort_skill_ids(fallback)

    def get_skill_domain(self, skill_id: str) -> str:
        self._validate_skill_id(skill_id)
        if '-' in skill_id:
            parts = skill_id.split('-')
            if len(parts) >= 2:
                code = parts[1]
                return {
                    'N': 'Numbers',
                    'F': 'Fractions',
                    'M': 'Measurement',
                    'G': 'Geometry',
                    'D': 'Data & Probability',
                }.get(code, code)

        caps_reference = str(self.skills_by_id[skill_id].get('caps_reference', '') or '').lower()
        if 'fraction' in caps_reference:
            return 'Fractions'
        if 'length' in caps_reference or 'mass' in caps_reference or 'capacity' in caps_reference or 'time' in caps_reference:
            return 'Measurement'
        if 'geometry' in caps_reference or 'shape' in caps_reference:
            return 'Geometry'
        if 'data' in caps_reference or 'probability' in caps_reference:
            return 'Data & Probability'
        return 'Numbers'

    def evaluate_answer(self, skill_id: str, is_correct: bool) -> list[str]:
        self._validate_skill_id(skill_id)
        self.tested_skill_ids.add(skill_id)

        if not is_correct:
            return self._sort_skill_ids(self.prerequisites_by_skill.get(skill_id, ()))

        self.assumed_known_skill_ids.update(self.get_all_prerequisites(skill_id))

        remaining_terminal_nodes = [
            candidate_id
            for candidate_id in self.terminal_skill_ids
            if candidate_id != skill_id and candidate_id not in self.tested_skill_ids
        ]
        if remaining_terminal_nodes:
            return self._sort_skill_ids(remaining_terminal_nodes)

        fallback_candidates = [
            candidate_id
            for candidate_id in self.skills_by_id
            if candidate_id != skill_id
            and candidate_id not in self.tested_skill_ids
            and candidate_id not in self.assumed_known_skill_ids
        ]
        return self._sort_skill_ids(fallback_candidates)

    def get_all_prerequisites(self, skill_id: str) -> set[str]:
        self._validate_skill_id(skill_id)
        return self._walk_prerequisites(skill_id, set())

    def get_all_downstream_dependencies(self, skill_id: str) -> set[str]:
        self._validate_skill_id(skill_id)
        return self._walk_dependents(skill_id, set())

    def get_sorted_skill_ids(self) -> list[str]:
        return self._sort_skill_ids(self.skills_by_id.keys())

    def _load_records(self, graph_path: str) -> list[dict[str, Any]]:
        path = Path(graph_path)
        if not path.is_absolute():
            path = Path(__file__).resolve().parent.parent / graph_path

        with path.open('r', encoding='utf-8') as file:
            data = json.load(file)

        if not isinstance(data, list):
            raise ValueError('caps_graph.json must contain a list of skill records.')
        return data

    def _build_indexes(self, records: list[dict[str, Any]]) -> None:
        referenced_skill_ids: set[str] = set()

        normalized_records: dict[str, dict[str, Any]] = {}
        for raw_record in records:
            skill_id = str(raw_record['skill_id']).strip()
            prerequisites = [
                prerequisite_id.strip()
                for prerequisite_id in raw_record.get('prerequisites', [])
                if prerequisite_id and prerequisite_id.strip()
            ]
            normalized_records[skill_id] = {
                **raw_record,
                'skill_id': skill_id,
                'prerequisites': list(dict.fromkeys(prerequisites)),
                'difficulty': float(raw_record.get('difficulty', 0.0) or 0.0),
            }

        for record in list(normalized_records.values()):
            for prerequisite_id in record['prerequisites']:
                referenced_skill_ids.add(prerequisite_id)
                if prerequisite_id not in normalized_records:
                    normalized_records[prerequisite_id] = {
                        'skill_id': prerequisite_id,
                        'skill_name': prerequisite_id,
                        'prerequisites': [],
                        'difficulty': 0.0,
                    }

        dependents: dict[str, list[str]] = {skill_id: [] for skill_id in normalized_records}
        for skill_id, record in normalized_records.items():
            self.skills_by_id[skill_id] = record
            self.prerequisites_by_skill[skill_id] = tuple(record['prerequisites'])
            self.difficulty_by_skill[skill_id] = record['difficulty']
            dependents.setdefault(skill_id, [])
            for prerequisite_id in record['prerequisites']:
                dependents.setdefault(prerequisite_id, []).append(skill_id)

        self.dependents_by_skill = {
            skill_id: tuple(self._sort_skill_ids(children))
            for skill_id, children in dependents.items()
        }

        terminal_nodes = [
            skill_id for skill_id in normalized_records if skill_id not in referenced_skill_ids
        ]
        self.terminal_skill_ids = tuple(self._sort_skill_ids(terminal_nodes))

    def _sort_skill_ids(self, skill_ids: Iterable[str]) -> list[str]:
        unique_skill_ids = list(dict.fromkeys(skill_ids))
        return sorted(
            unique_skill_ids,
            key=lambda skill_id: (-self.difficulty_by_skill.get(skill_id, 0.0), skill_id),
        )

    def _validate_skill_id(self, skill_id: str) -> None:
        if skill_id not in self.skills_by_id:
            raise ValueError(f"Unknown skill_id '{skill_id}'.")

    def _walk_prerequisites(self, skill_id: str, visited: set[str]) -> set[str]:
        for prerequisite_id in self.prerequisites_by_skill.get(skill_id, ()): 
            if prerequisite_id in visited:
                continue
            visited.add(prerequisite_id)
            self._walk_prerequisites(prerequisite_id, visited)
        return visited

    def _walk_dependents(self, skill_id: str, visited: set[str]) -> set[str]:
        for dependent_id in self.dependents_by_skill.get(skill_id, ()): 
            if dependent_id in visited:
                continue
            visited.add(dependent_id)
            self._walk_dependents(dependent_id, visited)
        return visited


def initialize_diagnostic_state(skill_ids: list[str]) -> dict[str, str]:
    return {skill_id: 'unknown' for skill_id in skill_ids}


def _graph_from_edges(edges: list[dict[str, str]], skill_ids: Optional[Iterable[str]] = None) -> DiagnosticGraph:
    return DiagnosticGraph.from_edges(edges, skill_ids=skill_ids)


def get_all_prerequisites(skill_id: str, edges: list[dict[str, str]], visited: set | None = None) -> set[str]:
    graph = _graph_from_edges(edges)
    prerequisites = graph.get_all_prerequisites(skill_id)
    if visited is not None:
        visited.update(prerequisites)
        return visited
    return prerequisites


def get_all_downstream_dependencies(skill_id: str, edges: list[dict[str, str]], visited: set | None = None) -> set[str]:
    graph = _graph_from_edges(edges)
    dependencies = graph.get_all_downstream_dependencies(skill_id)
    if visited is not None:
        visited.update(dependencies)
        return visited
    return dependencies


def process_diagnostic_answer(
    skill_id: str,
    is_correct: bool,
    current_state: dict[str, str],
    edges: list[dict[str, str]],
) -> dict[str, str]:
    graph = _graph_from_edges(edges, skill_ids=current_state.keys())
    updated_state = current_state.copy()

    if is_correct:
        updated_state[skill_id] = 'mastered'
        for prerequisite_id in graph.get_all_prerequisites(skill_id):
            if updated_state.get(prerequisite_id) == 'unknown':
                updated_state[prerequisite_id] = 'assumed_mastered'
        return updated_state

    updated_state[skill_id] = 'gap'
    for dependent_id in graph.get_all_downstream_dependencies(skill_id):
        if updated_state.get(dependent_id) == 'unknown':
            updated_state[dependent_id] = 'assumed_gap'
    return updated_state


def is_diagnostic_complete(current_state: dict[str, str], question_count: int, max_questions: int = 30) -> bool:
    if question_count >= max_questions:
        return True
    return all(state != 'unknown' for state in current_state.values())


def calculate_node_weight(skill_id: str, current_state: dict[str, str], edges: list[dict[str, str]]) -> int:
    graph = _graph_from_edges(edges, skill_ids=current_state.keys())
    unknown_prerequisites = [
        prerequisite_id
        for prerequisite_id in graph.get_all_prerequisites(skill_id)
        if current_state.get(prerequisite_id) == 'unknown'
    ]
    unknown_dependents = [
        dependent_id
        for dependent_id in graph.get_all_downstream_dependencies(skill_id)
        if current_state.get(dependent_id) == 'unknown'
    ]
    return min(len(unknown_prerequisites), len(unknown_dependents))


def select_next_diagnostic_skill(current_state: dict[str, str], edges: list[dict[str, str]]) -> Optional[str]:
    unknown_skill_ids = [
        skill_id for skill_id, state in current_state.items() if state == 'unknown'
    ]
    if not unknown_skill_ids:
        return None

    graph = _graph_from_edges(edges, skill_ids=current_state.keys())
    starting_candidates = [
        skill_id for skill_id in graph.get_starting_nodes() if skill_id in unknown_skill_ids
    ]
    if starting_candidates:
        return starting_candidates[0]

    ordered_unknown_skills = [
        skill_id for skill_id in graph.get_sorted_skill_ids() if skill_id in unknown_skill_ids
    ]
    if ordered_unknown_skills:
        return ordered_unknown_skills[0]

    return sorted(unknown_skill_ids)[0]
