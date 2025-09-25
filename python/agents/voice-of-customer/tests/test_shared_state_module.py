"""Tests covering the shared state utilities."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Importing the stub ensures the lightweight google.adk modules are available.
from ._tool_context_stub import get_tool_context_class  # noqa: E402  # isort: skip

# Ensure package is importable regardless of pytest working directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_of_customer.shared import state as shared_state  # noqa: E402  # isort: skip


FIXTURE_PATH = (
    Path(__file__).resolve().parents[0] / "fixtures" / "demo_state.json"
)


def test_ensure_default_state_initializes_missing_keys() -> None:
    state: dict[str, object] = {}

    shared_state.ensure_default_state(state)

    defaults = shared_state.default_state()
    for key in defaults:
        assert key in state
        assert state[key] == defaults[key]


def test_initialize_state_applies_fixture(tmp_path: Path) -> None:
    fixture_data = {
        "state": {
            shared_state.SharedStateKeys.PLAN_METADATA: {
                "request_summary": "Revisar onboarding",
                "audience": "Diretoria",
            },
            shared_state.SharedStateKeys.REPORTER_HANDOFF: {
                "status": "ready",
                "final_deliverable": "Deck pronto",
            },
        }
    }
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture_data), encoding="utf-8")

    state: dict[str, object] = {}
    shared_state.initialize_state(state, fixture=fixture_data["state"])

    assert state[shared_state.SharedStateKeys.PLAN_METADATA]["audience"] == "Diretoria"
    assert (
        state[shared_state.SharedStateKeys.REPORTER_HANDOFF]["final_deliverable"]
        == "Deck pronto"
    )


def test_before_agent_callback_loads_defaults_and_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    from google.adk.agents.callback_context import CallbackContext

    monkeypatch.setenv(shared_state.SCENARIO_ENV_VAR, str(FIXTURE_PATH))

    context = CallbackContext()
    shared_state.load_default_state(context)

    assert (
        context.state[shared_state.SharedStateKeys.PLAN_METADATA]["request_summary"]
        == "Diagnóstico do onboarding digital"
    )
    assert context.state[shared_state.SharedStateKeys.COLLECTED_DATASETS]


def test_root_agent_registers_before_agent_callback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(shared_state.SCENARIO_ENV_VAR, str(FIXTURE_PATH))

    from voice_of_customer.agent import root_agent
    from google.adk.agents.callback_context import CallbackContext

    assert callable(root_agent.before_agent_callback)

    # Ensure the stub modules are initialised for downstream imports.
    get_tool_context_class()

    callback_context = CallbackContext()
    root_agent.before_agent_callback(callback_context)

    assert callback_context.state[shared_state.SharedStateKeys.COLLECTED_DATASETS]

