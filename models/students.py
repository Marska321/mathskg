from typing import Any

from pydantic import BaseModel, Field


class MasterySkillRecord(BaseModel):
    skill_id: str
    status: str
    current_streak: int = 0
    error_patterns: dict[str, int] = Field(default_factory=dict)
    active_repair_path: list[str] = Field(default_factory=list)


class StudentMasteryResponse(BaseModel):
    student_id: str
    summary: dict[str, int]
    skills: list[MasterySkillRecord]


class RepairPathItem(BaseModel):
    source_skill_id: str
    repair_path: list[str]


class StudentRepairPathResponse(BaseModel):
    student_id: str
    items: list[RepairPathItem]


class StudentReportResponse(BaseModel):
    student_id: str
    summary: dict[str, Any]
    mastery_breakdown: dict[str, int]
    recent_repairs: list[RepairPathItem]
