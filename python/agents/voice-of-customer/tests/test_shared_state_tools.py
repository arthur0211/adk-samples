"""Unit tests for the shared state helper tools."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from ._tool_context_stub import get_tool_context_class  # noqa: E402  # isort: skip

# Ensure package imports resolve regardless of pytest working dir
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_of_customer.shared.state import SharedStateKeys  # noqa: E402  # isort: skip
from voice_of_customer.tools import (  # noqa: E402  # isort: skip
    get_reporter_snapshot,
    record_dataset,
    record_plan_metadata,
    record_quali_summary,
    record_quanti_summary,
    record_reporter_handoff,
)


@pytest.fixture()
def tool_context():
    tool_context_cls = get_tool_context_class()
    return tool_context_cls()


def test_recorders_update_state_and_return_status(tool_context) -> None:
    metadata_response = record_plan_metadata(
        {"request_summary": "Análise churn", "audience": "CS"},
        tool_context,
    )
    assert metadata_response["status"] == "plan_metadata_recorded"

    dataset_response = record_dataset(
        {"name": "nps_dataset", "timeframe": "2024-Q1"},
        tool_context,
    )
    assert dataset_response["status"] == "dataset_recorded"
    assert dataset_response["total_datasets"] == 1

    quant_response = record_quanti_summary(
        "NPS caiu 5 pontos",
        {"nps": 42.0, "csat": 4.5},
        tool_context,
    )
    assert quant_response["status"] == "quant_summary_recorded"
    assert quant_response["metrics_count"] == 2

    quali_response = record_quali_summary(
        "Sentimento negativo em onboarding",
        ["Onboarding", "Suporte"],
        ["Processo demorado"],
        tool_context,
    )
    assert quali_response["status"] == "qual_summary_recorded"
    assert quali_response["themes_count"] == 2
    assert quali_response["quotes_count"] == 1

    handoff_response = record_reporter_handoff(
        "Relatório executivo", ["Enviar para diretoria"], "ready", tool_context
    )
    assert handoff_response["status"] == "reporter_handoff_recorded"
    assert handoff_response["handoff_ready"] is True

    state = tool_context.state
    assert state[SharedStateKeys.COLLECTED_DATASETS][0]["name"] == "nps_dataset"
    assert state[SharedStateKeys.QUANT_INSIGHTS]["metrics"][0]["name"] == "nps"
    assert "Processo demorado" in state[SharedStateKeys.QUAL_INSIGHTS][
        "representative_quotes"
    ]
    assert state[SharedStateKeys.REPORTER_HANDOFF]["status"] == "ready"


def test_reporter_snapshot_reflects_recorded_entries(tool_context) -> None:
    record_dataset({"name": "csat_dataset"}, tool_context)
    record_quanti_summary("CSAT estável", None, tool_context)
    record_quali_summary("Clientes satisfeitos", ["Suporte"], None, tool_context)
    record_reporter_handoff("Resumo enviado", ["Coletar feedback"], "completed", tool_context)

    snapshot = get_reporter_snapshot(tool_context)

    assert snapshot[SharedStateKeys.COLLECTED_DATASETS][0]["name"] == "csat_dataset"
    assert snapshot[SharedStateKeys.QUANT_INSIGHTS]["summary"] == "CSAT estável"
    assert snapshot[SharedStateKeys.QUAL_INSIGHTS]["themes"] == ["Suporte"]
    assert snapshot[SharedStateKeys.REPORTER_HANDOFF]["status"] == "completed"
