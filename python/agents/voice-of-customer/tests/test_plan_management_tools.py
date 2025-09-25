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

PREREQ_PLAN = json.dumps(
    [
        {
            "tasks": [
                {
                    "execution_order": 1,
                    "task_description": "Confirmar datas de análise com o solicitante.",
                    "agent_name": "supervisor_agent",
                },
                {
                    "execution_order": 2,
                    "task_description": "Registrar canais prioritários (chat, e-mail, telefone).",
                    "agent_name": "supervisor_agent",
                },
                {
                    "execution_order": 3,
                    "task_description": "Validar objetivos estratégicos do estudo.",
                    "agent_name": "supervisor_agent",
                },
                {
                    "execution_order": 4,
                    "task_description": "Consolidar base agregada de feedbacks.",
                    "agent_name": "data_collector_agent",
                },
                {
                    "execution_order": 5,
                    "task_description": "Produzir métricas quantitativas sobre NPS.",
                    "agent_name": "quanti_analyst_agent",
                },
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

def test_ensure_next_task_ready_blocks_until_prereqs_done(tool_context) -> None:
    plan_management.store_supervisor_plan(PREREQ_PLAN, tool_context)

    response = plan_management.ensure_next_task_ready(
        "data_collector_agent", tool_context
    )

    assert response["status"] == "blocked"
    assert response["error"] == "prerequisites_incomplete"
    assert len(response["blocking_tasks"]) == 3
    assert all(
        task["agent_name"] == "supervisor_agent"
        for task in response["blocking_tasks"]
    )
    assert "datas" in response["message"]

    for order in ("1", "2", "3"):
        plan_management.mark_supervisor_task_completed(order, tool_context)

    ready = plan_management.ensure_next_task_ready(
        "data_collector_agent", tool_context
    )

    assert ready["status"] == "ready"
    assert ready["next_task"]["agent_name"] == "data_collector_agent"


def test_ensure_next_task_ready_requires_data_before_analysis(tool_context) -> None:
    plan_management.store_supervisor_plan(PREREQ_PLAN, tool_context)

    for order in ("1", "2", "3"):
        plan_management.mark_supervisor_task_completed(order, tool_context)

    response = plan_management.ensure_next_task_ready(
        "quanti_analyst_agent", tool_context
    )

    assert response["status"] == "blocked"
    assert response["error"] == "data_not_ready"
    assert all(
        task["agent_name"] == "data_collector_agent"
        for task in response["blocking_tasks"]
    )

    plan_management.mark_supervisor_task_completed("4", tool_context)

    ready = plan_management.ensure_next_task_ready(
        "quanti_analyst_agent", tool_context
    )

    assert ready["status"] == "ready"
    assert ready["next_task"]["agent_name"] == "quanti_analyst_agent"
