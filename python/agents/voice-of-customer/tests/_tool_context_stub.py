"""Helpers to provide a ToolContext stub when google.adk is unavailable."""

from __future__ import annotations

import sys
import types
from typing import Any, Type


def ensure_tool_context_stub() -> None:
    """Injects lightweight google.adk modules with a ToolContext stub."""

    if "google" not in sys.modules:  # pragma: no cover - module import guard
        google_module = types.ModuleType("google")
        google_module.__path__ = []
        sys.modules["google"] = google_module
    else:  # pragma: no cover - reuse existing module when provided by environment
        google_module = sys.modules["google"]

    if "google.adk" not in sys.modules:  # pragma: no cover - module import guard
        adk_module = types.ModuleType("google.adk")
        adk_module.__path__ = []
        sys.modules["google.adk"] = adk_module
        setattr(google_module, "adk", adk_module)
    else:  # pragma: no cover - reuse existing module when provided by environment
        adk_module = sys.modules["google.adk"]
        setattr(google_module, "adk", adk_module)

    if "google.adk.tools" not in sys.modules:  # pragma: no cover - module import guard
        tools_module = types.ModuleType("google.adk.tools")

        class _StubToolContext:
            """Minimal stand-in exposing the ``state`` attribute used by the tools."""

            def __init__(self) -> None:
                self.state: dict[str, Any] = {}

        tools_module.ToolContext = _StubToolContext
        tools_module.__all__ = ["ToolContext"]
        sys.modules["google.adk.tools"] = tools_module
        setattr(adk_module, "tools", tools_module)
    else:  # pragma: no cover - reuse existing module
        tools_module = sys.modules["google.adk.tools"]
        setattr(adk_module, "tools", tools_module)


def get_tool_context_class() -> Type[Any]:
    """Returns the ToolContext class, stubbing it if necessary."""

    ensure_tool_context_stub()
    from google.adk.tools import ToolContext

    return ToolContext


__all__ = ["ensure_tool_context_stub", "get_tool_context_class"]


# Ensure the stub is available as soon as the helper module is imported.
ensure_tool_context_stub()
