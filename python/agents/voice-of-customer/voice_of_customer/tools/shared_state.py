"""Tools that manage shared Voice of Customer session state."""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from google.adk.tools import ToolContext

from ..shared.state import (
    SharedStateKeys,
    build_reporter_snapshot,
    ensure_default_state,
)


def record_plan_metadata(
    metadata: Mapping[str, Any], tool_context: ToolContext
) -> dict[str, Any]:
    """Stores planner metadata emitted by the supervisor or planner."""

    ensure_default_state(tool_context.state)
    if not isinstance(metadata, Mapping):
        return {"status": "error", "error": "metadata_must_be_mapping"}

    plan_metadata = _get_mutable_dict(
        tool_context.state, SharedStateKeys.PLAN_METADATA
    )
    plan_metadata.update(dict(metadata))
    return {
        "status": "plan_metadata_recorded",
        "metadata": dict(plan_metadata),
    }


def record_dataset(dataset: Mapping[str, Any], tool_context: ToolContext) -> dict[str, Any]:
    """Registers a dataset collected by the data_collector_agent."""

    ensure_default_state(tool_context.state)
    if not isinstance(dataset, Mapping):
        return {"status": "error", "error": "dataset_must_be_mapping"}

    dataset_entry = dict(dataset)
    dataset_name = str(dataset_entry.get("name", "")).strip()
    if not dataset_name:
        return {"status": "error", "error": "dataset_name_required"}
    dataset_entry["name"] = dataset_name

    datasets = _get_mutable_list(
        tool_context.state, SharedStateKeys.COLLECTED_DATASETS
    )
    for index, existing in enumerate(datasets):
        if isinstance(existing, Mapping) and existing.get("name") == dataset_name:
            datasets[index] = dataset_entry
            break
    else:
        datasets.append(dataset_entry)

    return {
        "status": "dataset_recorded",
        "dataset": dataset_entry,
        "total_datasets": len(datasets),
    }


def record_quanti_summary(
    summary: str,
    metrics: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Stores quantitative analysis outputs."""

    ensure_default_state(tool_context.state)
    summary_text = str(summary).strip()
    quant_state = _get_mutable_dict(
        tool_context.state, SharedStateKeys.QUANT_INSIGHTS
    )
    quant_state["summary"] = summary_text
    quant_state["metrics"] = _normalise_metrics(metrics)

    return {
        "status": "quant_summary_recorded",
        "summary": summary_text,
        "metrics_count": len(quant_state["metrics"]),
    }


def record_quali_summary(
    summary: str,
    themes: Sequence[str] | None,
    representative_quotes: Sequence[str] | None,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Stores qualitative insights such as themes and representative quotes."""

    ensure_default_state(tool_context.state)
    quali_state = _get_mutable_dict(
        tool_context.state, SharedStateKeys.QUAL_INSIGHTS
    )
    quali_state["summary"] = str(summary).strip()
    quali_state["themes"] = _normalise_string_sequence(themes)
    quali_state["representative_quotes"] = _normalise_string_sequence(
        representative_quotes
    )

    return {
        "status": "qual_summary_recorded",
        "themes_count": len(quali_state["themes"]),
        "quotes_count": len(quali_state["representative_quotes"]),
    }


def record_reporter_handoff(
    final_deliverable: str,
    next_steps: Sequence[str] | None,
    status: str,
    tool_context: ToolContext,
) -> dict[str, Any]:
    """Persists the final reporter hand-off information."""

    ensure_default_state(tool_context.state)
    handoff_state = _get_mutable_dict(
        tool_context.state, SharedStateKeys.REPORTER_HANDOFF
    )
    handoff_state["final_deliverable"] = str(final_deliverable).strip()
    handoff_state["next_steps"] = _normalise_string_sequence(next_steps)
    handoff_state["status"] = str(status).strip() or "pending"

    return {
        "status": "reporter_handoff_recorded",
        "handoff_ready": handoff_state["status"].lower() in {"ready", "completed"},
    }


def get_reporter_snapshot(tool_context: ToolContext) -> dict[str, Any]:
    """Returns an aggregated snapshot of the shared state for the reporter."""

    ensure_default_state(tool_context.state)
    return build_reporter_snapshot(tool_context.state)


def _get_mutable_dict(state: MutableMapping[str, Any], key: str) -> MutableMapping[str, Any]:
    value = state.get(key)
    if not isinstance(value, MutableMapping):
        value = {}
        state[key] = value
    return value


def _get_mutable_list(state: MutableMapping[str, Any], key: str) -> list[Any]:
    value = state.get(key)
    if not isinstance(value, list):
        value = []
        state[key] = value
    return value


def _normalise_metrics(
    metrics: Mapping[str, Any] | Sequence[Mapping[str, Any]] | None
) -> list[dict[str, Any]]:
    if metrics is None:
        return []
    if isinstance(metrics, Mapping):
        return [
            {"name": str(name), "value": value}
            for name, value in metrics.items()
        ]
    if isinstance(metrics, Sequence):
        normalised: list[dict[str, Any]] = []
        for item in metrics:
            if isinstance(item, Mapping):
                normalised.append(dict(item))
        return normalised
    return []


def _normalise_string_sequence(values: Sequence[str] | None) -> list[str]:
    if not values:
        return []
    return [str(value).strip() for value in values if str(value).strip()]


__all__ = [
    "record_plan_metadata",
    "record_dataset",
    "record_quanti_summary",
    "record_quali_summary",
    "record_reporter_handoff",
    "get_reporter_snapshot",
]
