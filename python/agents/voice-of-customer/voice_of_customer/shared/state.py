"""Utilities for initializing and managing shared VoC session state."""

from __future__ import annotations

import copy
import json
import os
from dataclasses import dataclass
from typing import Any, Mapping, MutableMapping

from google.adk.agents.callback_context import CallbackContext

SCENARIO_ENV_VAR = "VOICE_OF_CUSTOMER_SCENARIO"


@dataclass(frozen=True)
class SharedStateKeys:
    """Canonical keys used by sub-agents to exchange information."""

    PLAN_METADATA: str = "plan_metadata"
    COLLECTED_DATASETS: str = "collected_datasets"
    QUANT_INSIGHTS: str = "quantitative_insights"
    QUAL_INSIGHTS: str = "qualitative_insights"
    REPORTER_HANDOFF: str = "reporter_handoff"


def default_state() -> dict[str, Any]:
    """Returns a fresh copy of the default shared state structure."""

    return {
        SharedStateKeys.PLAN_METADATA: {
            "request_summary": "",
            "timeframe": "",
            "audience": "",
        },
        SharedStateKeys.COLLECTED_DATASETS: [],
        SharedStateKeys.QUANT_INSIGHTS: {
            "summary": "",
            "metrics": [],
        },
        SharedStateKeys.QUAL_INSIGHTS: {
            "summary": "",
            "themes": [],
            "representative_quotes": [],
        },
        SharedStateKeys.REPORTER_HANDOFF: {
            "status": "pending",
            "final_deliverable": "",
            "next_steps": [],
        },
    }


def ensure_default_state(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    """Ensures that ``state`` contains all expected shared-state keys."""

    defaults = default_state()
    for key, value in defaults.items():
        if key not in state:
            state[key] = copy.deepcopy(value)
            continue

        if isinstance(value, dict) and isinstance(state[key], MutableMapping):
            for nested_key, nested_value in value.items():
                state[key].setdefault(nested_key, copy.deepcopy(nested_value))

    return state


def _deep_update(target: MutableMapping[str, Any], updates: Mapping[str, Any]) -> None:
    """Performs a deep update of ``target`` with ``updates``."""

    for key, value in updates.items():
        if isinstance(value, Mapping) and isinstance(target.get(key), MutableMapping):
            _deep_update(target[key], value)
        else:
            target[key] = copy.deepcopy(value)


def initialize_state(
    state: MutableMapping[str, Any], fixture: Mapping[str, Any] | None = None
) -> MutableMapping[str, Any]:
    """Initializes ``state`` with defaults and optional fixture data."""

    ensure_default_state(state)
    if fixture:
        _deep_update(state, fixture)
    return state


def _load_fixture(path: str) -> Mapping[str, Any]:
    """Loads a fixture file returning the contained state mapping."""

    with open(path, "r", encoding="utf-8") as file:
        payload = json.load(file)
    if isinstance(payload, Mapping) and "state" in payload:
        state_payload = payload["state"]
        if isinstance(state_payload, Mapping):
            return state_payload
    if not isinstance(payload, Mapping):  # pragma: no cover - sanity guard
        raise ValueError("Fixture payload must be a mapping")
    return payload


def load_default_state(callback_context: CallbackContext) -> None:
    """Callback that seeds the shared state before the supervisor runs."""

    fixture_path = os.getenv(SCENARIO_ENV_VAR)
    fixture_data: Mapping[str, Any] | None = None
    if fixture_path:
        fixture_data = _load_fixture(fixture_path)

    initialize_state(callback_context.state, fixture=fixture_data)


def build_reporter_snapshot(state: Mapping[str, Any]) -> dict[str, Any]:
    """Returns an immutable snapshot that the reporter can safely consume."""

    snapshot = {}
    defaults = default_state()
    for key, default_value in defaults.items():
        if key not in state:
            snapshot[key] = copy.deepcopy(default_value)
            continue
        value = state[key]
        if isinstance(value, Mapping):
            snapshot[key] = copy.deepcopy(dict(value))
        else:
            snapshot[key] = copy.deepcopy(value)
    return snapshot


__all__ = [
    "SharedStateKeys",
    "SCENARIO_ENV_VAR",
    "default_state",
    "ensure_default_state",
    "initialize_state",
    "load_default_state",
    "build_reporter_snapshot",
]
