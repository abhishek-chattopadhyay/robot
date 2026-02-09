from __future__ import annotations

from fastapi import FastAPI

from pbpk_backend.api.orchestrator import router as orchestrator_router

app = FastAPI(title="PBPK FAIR Platform API (v1)")
app.include_router(orchestrator_router)