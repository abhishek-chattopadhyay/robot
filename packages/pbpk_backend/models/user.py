from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class User:
    orcid: str
    name: Optional[str] = None
    created_at: Optional[str] = None
    last_login_at: Optional[str] = None
