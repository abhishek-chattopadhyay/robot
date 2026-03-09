from fastapi import FastAPI

from pbpk_backend.api.orchestrator import router as orchestrator_router
from pbpk_backend.api.auth import router as auth_router
from pbpk_backend.api.ai import router as ai_router
from pbpk_backend.api.form_spec import router as form_spec_router
from pbpk_backend.api import patches as patches_api
from pbpk_backend.api import array_ops as array_ops_api
from pbpk_backend.api import templates as templates_api
from pbpk_backend.api import form_ui as form_ui_api
from pbpk_backend.api import drafts as drafts_api
from pbpk_backend.api import draft_apply
from pbpk_backend.api import ui_static

app = FastAPI(title="PBPK FAIR Platform API (v1)")

app.include_router(orchestrator_router)
app.include_router(auth_router)
app.include_router(ai_router)
app.include_router(form_spec_router)
app.include_router(patches_api.router)
app.include_router(array_ops_api.router)
app.include_router(templates_api.router)
app.include_router(form_ui_api.router)
app.include_router(drafts_api.router)
app.include_router(draft_apply.router)
app.include_router(ui_static.router)