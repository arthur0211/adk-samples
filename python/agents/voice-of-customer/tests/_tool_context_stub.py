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

    if "google.adk.agents" not in sys.modules:  # pragma: no cover - module import guard
        agents_module = types.ModuleType("google.adk.agents")

        class _StubLlmAgent:
            """Lightweight replacement that stores init kwargs as attributes."""

            def __init__(self, *args: Any, **kwargs: Any) -> None:  # noqa: D401 - simple stub
                self._args = args
                self._kwargs = kwargs
                for key, value in kwargs.items():
                    setattr(self, key, value)

        agents_module.LlmAgent = _StubLlmAgent
        agents_module.__all__ = ["LlmAgent"]
        sys.modules["google.adk.agents"] = agents_module
        setattr(adk_module, "agents", agents_module)
    else:  # pragma: no cover - reuse existing module
        agents_module = sys.modules["google.adk.agents"]
        setattr(adk_module, "agents", agents_module)

    if "google.adk.agents.callback_context" not in sys.modules:  # pragma: no cover
        callback_module = types.ModuleType("google.adk.agents.callback_context")

        class _StubCallbackContext:
            """Minimal callback context exposing a mutable state mapping."""

            def __init__(self) -> None:
                self.state: dict[str, Any] = {}

        callback_module.CallbackContext = _StubCallbackContext
        callback_module.__all__ = ["CallbackContext"]
        sys.modules["google.adk.agents.callback_context"] = callback_module
        setattr(agents_module, "callback_context", callback_module)
    else:  # pragma: no cover - reuse existing module when provided by environment
        callback_module = sys.modules["google.adk.agents.callback_context"]
        setattr(agents_module, "callback_context", callback_module)

    if "google.adk.tools" not in sys.modules:  # pragma: no cover - module import guard
        tools_module = types.ModuleType("google.adk.tools")

        class _StubToolContext:
            """Minimal stand-in exposing the ``state`` attribute used by the tools."""

            def __init__(self) -> None:
                self.state: dict[str, Any] = {}

        class _StubFunctionTool:
            """No-op FunctionTool that proxies calls to the wrapped function."""

            def __init__(self, func: Any, *args: Any, **kwargs: Any) -> None:  # noqa: D401
                self.func = func
                self._args = args
                self._kwargs = kwargs

            def __call__(self, *args: Any, **kwargs: Any) -> Any:
                return self.func(*args, **kwargs)

        tools_module.ToolContext = _StubToolContext
        tools_module.FunctionTool = _StubFunctionTool
        tools_module.__all__ = ["ToolContext", "FunctionTool"]
        sys.modules["google.adk.tools"] = tools_module
        setattr(adk_module, "tools", tools_module)
    else:  # pragma: no cover - reuse existing module
        tools_module = sys.modules["google.adk.tools"]
        setattr(adk_module, "tools", tools_module)

    if "google.adk.tools.agent_tool" not in sys.modules:  # pragma: no cover
        agent_tool_module = types.ModuleType("google.adk.tools.agent_tool")

        class _StubAgentTool:
            """Stores a reference to the delegated agent."""

            def __init__(self, agent: Any, *args: Any, **kwargs: Any) -> None:  # noqa: D401
                self.agent = agent
                self._args = args
                self._kwargs = kwargs

        agent_tool_module.AgentTool = _StubAgentTool
        agent_tool_module.__all__ = ["AgentTool"]
        sys.modules["google.adk.tools.agent_tool"] = agent_tool_module
        setattr(tools_module, "agent_tool", agent_tool_module)
    else:  # pragma: no cover - reuse existing module when provided by environment
        agent_tool_module = sys.modules["google.adk.tools.agent_tool"]
        setattr(tools_module, "agent_tool", agent_tool_module)


def get_tool_context_class() -> Type[Any]:
    """Returns the ToolContext class, stubbing it if necessary."""

    ensure_tool_context_stub()
    from google.adk.tools import ToolContext

    return ToolContext


__all__ = ["ensure_tool_context_stub", "get_tool_context_class"]


# Ensure the stub is available as soon as the helper module is imported.
ensure_tool_context_stub()
