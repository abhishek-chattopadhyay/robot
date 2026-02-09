from fastapi import FastAPI

from pbpk_backend.api.orchestrator import router as orchestrator_router
from pbpk_backend.api.auth import router as auth_router

app = FastAPI(title="PBPK FAIR Platform API (v1)")
app.include_router(orchestrator_router)
app.include_router(auth_router)
