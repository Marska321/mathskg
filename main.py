from fastapi import FastAPI
from routers.diagnostic import router as diagnostic_router
from routers.submission import router as submission_router
from routers.dashboard import router as dashboard_router

app = FastAPI(title="Lumen Engine API")

app.include_router(dashboard_router)
app.include_router(submission_router)
app.include_router(diagnostic_router)
