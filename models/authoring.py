from typing import Any

from pydantic import BaseModel, Field, field_validator


class SkillAuthoringPayload(BaseModel):
    skill_id: str
    skill_name: str
    strand: str | None = None
    caps_reference: str | dict[str, Any] | None = None
    difficulty: float = 1.0
    failure_risk: str | None = None
    mastery_criteria: str | dict[str, Any] | None = None
    question_template: str = ""
    approval_status: str = "pending"

    @field_validator("skill_id", "skill_name")
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class SkillUpdatePayload(BaseModel):
    skill_name: str | None = None
    strand: str | None = None
    caps_reference: str | dict[str, Any] | None = None
    difficulty: float | None = None
    failure_risk: str | None = None
    mastery_criteria: str | dict[str, Any] | None = None
    question_template: str | None = None
    approval_status: str | None = None


class TemplateCreatePayload(BaseModel):
    skill_id: str
    template_id: str
    template_body: dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    status: str = "draft"

    @field_validator("skill_id", "template_id")
    @classmethod
    def validate_template_ids(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned


class PublishPayload(BaseModel):
    skill_id: str
    force: bool = False

    @field_validator("skill_id")
    @classmethod
    def validate_skill_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("skill_id must not be empty")
        return cleaned
