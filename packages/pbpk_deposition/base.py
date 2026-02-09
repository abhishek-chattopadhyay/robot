from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Protocol


@dataclass
class DepositionResult:
    ok: bool
    platform: str
    record_id: Optional[str] = None
    doi: Optional[str] = None
    url: Optional[str] = None
    message: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None


class BaseDepositor(Protocol):
    name: str

    def deposit(
        self,
        *,
        crate_dir: Path,
        metadata_path: Path,
        access_token: str,
        sandbox: bool = False,
        **kwargs: Any,
    ) -> DepositionResult:
        ...


_REGISTRY: Dict[str, type] = {}


def register(name: str):
    def _decorator(cls: type):
        _REGISTRY[name] = cls
        cls.name = name  # type: ignore[attr-defined]
        return cls
    return _decorator


def get_depositor(name: str) -> type:
    if name not in _REGISTRY:
        raise KeyError(f"Unknown depositor '{name}'. Available: {sorted(_REGISTRY)}")
    return _REGISTRY[name]


def available_depositors() -> list[str]:
    return sorted(_REGISTRY.keys())