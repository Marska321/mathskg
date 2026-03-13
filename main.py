from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.config import get_settings
from core.database import get_supabase
from routers.authoring import router as authoring_router
from routers.dashboard import router as dashboard_router
from routers.diagnostic import router as diagnostic_router
from routers.students import router as students_router
from routers.submission import router as submission_router
from routers.teacher import router as teacher_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    get_settings()
    get_supabase()
    yield


app = FastAPI(title="Lumen Engine API", lifespan=lifespan)

app.include_router(dashboard_router)
app.include_router(submission_router)
app.include_router(diagnostic_router)
app.include_router(students_router)
app.include_router(teacher_router)
app.include_router(authoring_router)
