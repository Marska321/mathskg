from pydantic import BaseModel, Field, field_validator, model_validator


class QuestionSchema(BaseModel):
    skill_id: str
    seed: str
    evidence_type: str
    question_text: str
    options: list[str]
    correct_answer: str
    hints: list[str]
    error_mapping: dict[str, str] = Field(default_factory=dict)

    @field_validator("options")
    @classmethod
    def check_options_length_and_uniqueness(cls, value: list[str]) -> list[str]:
        if len(value) != 4:
            raise ValueError(f"A multiple choice question must have exactly 4 options. Got {len(value)}.")
        if len(set(value)) != 4:
            raise ValueError("All options (including distractors) must be mathematically unique.")
        return value

    @model_validator(mode="after")
    def check_answer_in_options(self):
        if self.correct_answer not in self.options:
            raise ValueError("The correct_answer must be present in the generated options array.")
        return self


class AnswerSubmission(BaseModel):
    student_id: str
    skill_id: str
    student_answer: str
    correct_answer: str
    time_taken_seconds: float
    error_mapping: dict[str, str] = Field(default_factory=dict)
