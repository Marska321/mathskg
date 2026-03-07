from typing import Any

from pydantic import BaseModel, Field


class HeatmapSkillRow(BaseModel):
    skill_id: str
    mastered: int = 0
    learning: int = 0
    needs_review: int = 0
    unknown: int = 0
    percent_mastered: float = 0.0


class TeacherHeatmapResponse(BaseModel):
    class_id: str
    learners: int
    skills: list[HeatmapSkillRow]


class BottleneckRow(BaseModel):
    skill_id: str
    attempts: int
    failures: int
    failure_rate: float
    top_error_type: str | None = None


class TeacherBottlenecksResponse(BaseModel):
    class_id: str
    learners: int
    bottlenecks: list[BottleneckRow]


class CapsCoverageRow(BaseModel):
    topic: str
    skills_total: int
    skills_mastered_by_class: int
    coverage_percent: float


class TeacherCapsCoverageResponse(BaseModel):
    class_id: str
    learners: int
    summary: dict[str, Any]
    coverage: list[CapsCoverageRow] = Field(default_factory=list)
