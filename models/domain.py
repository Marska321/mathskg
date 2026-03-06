from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class MasteryStatus(str, Enum):
    UNKNOWN = "unknown"
    LEARNING = "learning"
    MASTERED = "mastered"
    NEEDS_REVIEW = "needs_review"
    ASSUMED_MASTERED = "assumed_mastered"
    GAP = "gap"
    ASSUMED_GAP = "assumed_gap"


class SkillEdge(BaseModel):
    skill_id: str
    prerequisite_id: str

    @field_validator("skill_id", "prerequisite_id")
    @classmethod
    def validate_non_empty_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("skill ids must not be empty")
        return cleaned


class GraphSkillRecord(BaseModel):
    skill_id: str
    skill_name: str
    prerequisites: list[str] = Field(default_factory=list)
    caps_reference: str | dict[str, Any] | None = None
    difficulty: float = 1.0
    mastery_criteria: str | dict[str, Any] | None = None
    question_template: str = ""

    @field_validator("skill_id", "skill_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned

    @field_validator("prerequisites")
    @classmethod
    def validate_prerequisites(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("prerequisites must not contain duplicates")
        return cleaned
