from pydantic import BaseModel

class PracticeRequest(BaseModel):
    student_id: str
    skill_id: str
