from __future__ import annotations

from pathlib import Path
from typing import Tuple

from rocrate_validator import models, services

from .interface import IssueList


def validate_rocrate_base(crate_dir: Path) -> Tuple[IssueList, IssueList]:
    """
    Validates a crate directory against the base RO-Crate 1.1 profile.
    Model-agnostic — suitable for any RO-Crate regardless of domain.
    Returns (errors, warnings).
    """
    settings = services.ValidationSettings(
        rocrate_uri=crate_dir,
        profile_identifier="ro-crate-1.1",
        requirement_severity=models.Severity.REQUIRED,
    )
    result = services.validate(settings)
    errors: IssueList = [
        {"code": issue.check.identifier, "node_id": "", "message": issue.message}
        for issue in result.get_issues()
    ]
    return errors, []
