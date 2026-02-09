from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import DepositionResult, register


@register("workflowhub")
class WorkflowHubDepositor:
    def deposit(
        self,
        *,
        crate_dir: Path,
        metadata_path: Path,
        access_token: str,
        sandbox: bool = False,
        **kwargs: Any,
    ) -> DepositionResult:
        return DepositionResult(
            ok=False,
            platform="workflowhub",
            message="WorkflowHub depositor not implemented yet (stub).",
        )