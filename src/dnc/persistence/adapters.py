"""Optional distributed adapter boundaries."""

from __future__ import annotations

import importlib.util


def ray_available() -> bool:
    return importlib.util.find_spec("ray") is not None


def temporal_available() -> bool:
    return importlib.util.find_spec("temporalio") is not None


def require_optional_adapter(name: str) -> None:
    available = {"ray": ray_available, "temporal": temporal_available}
    if name not in available:
        raise ValueError(f"unknown distributed adapter: {name}")
    if not available[name]():
        raise RuntimeError(f"optional {name} adapter is not installed")
