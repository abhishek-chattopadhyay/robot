from fastapi import FastAPI

from pbpk_backend.api.orchestrator import router as orchestrator_router
from pbpk_backend.api.auth import router as auth_router
from pbpk_backend.api.ai import router as ai_router
from pbpk_backend.api.form_spec import router as form_spec_router

app = FastAPI(title="PBPK FAIR Platform API (v1)")

app.include_router(orchestrator_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(form_spec_router)