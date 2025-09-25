"""Tests for the plan management FunctionTools exposed to the supervisor."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from ._tool_context_stub import get_tool_context_class  # noqa: E402  # isort: skip

# Ensure the package directory is importable regardless of the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_of_customer.shared.plan import PLAN_STATE_KEY  # noqa: E402  # isort: skip
from voice_of_customer.tools import plan_management  # noqa: E402  # isort: skip


INVALID_PLAN = "plan que não é json"
VALID_PLAN = json.dumps(
    [
        {
            "tasks": [
                {
                    "execution_order": 1,
                    "task_description": "Confirmar escopo com o solicitante.",
                    "agent_name": "supervisor_agent",
                }
            ],
            "completed": False,
        }
    ]
)


@pytest.fixture()
def tool_context():
    """Provides a ToolContext instance backed by an in-memory state."""

    tool_context_cls = get_tool_context_class()
    return tool_context_cls()


def test_store_plan_invalid_json_returns_error(tool_context) -> None:
    response = plan_management.store_supervisor_plan(INVALID_PLAN, tool_context)

    assert response["status"] == "error"
    assert response["error"] == "plan_parsing_error"
    assert PLAN_STATE_KEY not in tool_context.state

    narrated = plan_management.format_plan_tool_status(
        "store_supervisor_plan", response
    )
    assert narrated.startswith("store_supervisor_plan tool reported:")
    assert "plan parsing" not in narrated.lower()  # ensure Portuguese message is surfaced
    assert "Não foi possível interpretar o plano" in narrated


def test_mark_task_completed_without_plan_returns_error(tool_context) -> None:
    response = plan_management.mark_supervisor_task_completed("1", tool_context)

    assert response["status"] == "error"
    assert response["error"] == "plan_not_found"

    narrated = plan_management.format_plan_tool_status(
        "mark_supervisor_task_completed", response
    )
    assert narrated.startswith("mark_supervisor_task_completed tool reported:")
    assert response["message"] in narrated


def test_mark_task_completed_invalid_order_returns_error(tool_context) -> None:
    store_response = plan_management.store_supervisor_plan(VALID_PLAN, tool_context)
    assert store_response["status"] == "stored"

    response = plan_management.mark_supervisor_task_completed("99", tool_context)

    assert response["status"] == "error"
    assert response["error"] == "task_not_found"

    narrated = plan_management.format_plan_tool_status(
        "mark_supervisor_task_completed", response
    )
    assert "A tarefa informada não existe" in narrated


def test_get_plan_status_reports_absence_of_plan(tool_context) -> None:
    status = plan_management.get_supervisor_plan_status(tool_context)

    assert status["status"] == "plan_status"
    assert status["has_plan"] is False
    assert status["summary"]["total_tasks"] == 0
    assert "Nenhum plano ativo" in status["markdown"]

    narrated = plan_management.format_plan_tool_status(
        "get_supervisor_plan_status", status
    )
    assert narrated.startswith("get_supervisor_plan_status tool reported:")
    assert "Nenhum plano ativo" in narrated
