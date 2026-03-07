from fastapi import FastAPI

from core.config import validate_required_env
from routers.dashboard import router as dashboard_router
from routers.diagnostic import router as diagnostic_router
from routers.students import router as students_router
from routers.submission import router as submission_router

validate_required_env()

app = FastAPI(title="Lumen Engine API")

app.include_router(dashboard_router)
app.include_router(submission_router)
app.include_router(diagnostic_router)
app.include_router(students_router)
