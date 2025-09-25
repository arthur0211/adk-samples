"""Avenue Deep Dive Voice of Customer package."""

from importlib import import_module
from typing import Any

__all__ = ["root_agent", "supervisor_agent"]


def __getattr__(name: str) -> Any:  # pragma: no cover - thin convenience wrapper
    if name in __all__:
        module = import_module(".agent", __name__)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
