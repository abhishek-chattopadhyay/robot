from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Tuple

IssueList = List[Dict[str, str]]


class DomainValidator(Protocol):
    def __call__(
        self,
        rocrate: Dict[str, Any],
        *,
        crate_dir: Optional[Path] = None,
    ) -> Tuple[IssueList, IssueList]:
        """Returns (errors, warnings)."""
        ...
