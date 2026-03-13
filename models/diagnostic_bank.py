from pydantic import BaseModel, Field, field_validator


class DiagnosticAnchorQuestion(BaseModel):
    question_id: str
    grade_level: int = Field(default=4, ge=1, le=12)
    domain: str
    cluster: str
    skill_id: str
    question_text: str
    correct_answer: str
    difficulty: float = Field(default=1.0, ge=0.1, le=5.0)
    active: bool = True

    @field_validator(
        "question_id",
        "domain",
        "cluster",
        "skill_id",
        "question_text",
        "correct_answer",
    )
    @classmethod
    def validate_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("value must not be empty")
        return cleaned
