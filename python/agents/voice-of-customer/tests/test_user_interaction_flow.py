"""Simulates a realistic supervisor-to-user interaction leveraging plan tools."""

from __future__ import annotations

import json
import logging
import sys
import textwrap
from pathlib import Path

import pytest

from ._tool_context_stub import get_tool_context_class  # noqa: E402  # isort: skip

# Ensure the package directory is importable regardless of the working directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_of_customer.shared.plan import PLAN_STATE_KEY  # noqa: E402  # isort: skip
from voice_of_customer.tools import plan_management  # noqa: E402  # isort: skip


PLAN_PAYLOAD = json.dumps(
    [
        {
            "tasks": [
                {
                    "execution_order": 1,
                    "task_description": "Confirmar escopo com o solicitante e registrar requisitos adicionais.",
                    "agent_name": "supervisor_agent",
                    "task_completed": False,
                },
                {
                    "execution_order": 2,
                    "task_description": "Coletar métricas agregadas de NPS e CSAT dos últimos 12 meses.",
                    "agent_name": "data_collector_agent",
                    "task_completed": False,
                },
            ],
            "completed": False,
        },
        {
            "tasks": [
                {
                    "execution_order": 3,
                    "task_description": "Calcular tendências trimestrais com destaques para variações significativas.",
                    "agent_name": "quanti_analyst_agent",
                    "task_completed": False,
                },
                {
                    "execution_order": 4,
                    "task_description": "Identificar temas qualitativos recorrentes em feedbacks abertos.",
                    "agent_name": "quali_analyst_agent",
                    "task_completed": False,
                },
                {
                    "execution_order": 5,
                    "task_description": "Gerar relatório final consolidado com recomendações acionáveis.",
                    "agent_name": "reporter_agent",
                    "task_completed": False,
                },
            ],
            "completed": False,
        },
    ],
    ensure_ascii=False,
    indent=2,
)

# Prefix with natural language to mimic how the planner responds in practice.
PLANNER_RESPONSE = textwrap.dedent(
    f"""
    Plano final preparado pelo planner_agent:
    {PLAN_PAYLOAD}
    """
)


@pytest.mark.parametrize("orders", [["1", "2", "3", "4", "5"]])
def test_user_like_interaction_flow(orders, caplog: pytest.LogCaptureFixture) -> None:
    """Emulates a realistic user journey across plan management tools."""

    tool_context_cls = get_tool_context_class()
    tool_context = tool_context_cls()

    with caplog.at_level(logging.INFO):
        store_response = plan_management.store_supervisor_plan(
            PLANNER_RESPONSE, tool_context
        )
        assert store_response["status"] == "stored"
        assert store_response["total_tasks"] == len(orders)
        assert store_response["pending_tasks"] == len(orders)
        assert store_response["stages"] == 2
        assert store_response["has_plan"] is True
        assert PLAN_STATE_KEY in tool_context.state

        status_snapshot = plan_management.get_supervisor_plan_status(tool_context)
        assert status_snapshot["summary"]["total_tasks"] == len(orders)
        assert status_snapshot["summary"]["remaining_tasks"] == len(orders)
        assert "## Plano de tarefas do supervisor" in status_snapshot["markdown"]
        assert "### Etapa 1" in status_snapshot["markdown"]
        assert status_snapshot["has_plan"] is True

        for index, order in enumerate(orders, start=1):
            response = plan_management.mark_supervisor_task_completed(order, tool_context)
            assert response["status"] == "task_completed"
            assert response["execution_order"] == order
            assert response["total_completed"] == index
            assert response["remaining_tasks"] == len(orders) - index

        final_status = plan_management.get_supervisor_plan_status(tool_context)
        assert final_status["summary"]["completed_tasks"] == len(orders)
        assert final_status["summary"]["remaining_tasks"] == 0
        assert final_status["summary"]["completed_stages"] == 2
        assert "### Etapa 1 ✅" in final_status["markdown"]
        assert "### Etapa 2 ✅" in final_status["markdown"]
        assert final_status["has_plan"] is True

        reset_response = plan_management.reset_supervisor_plan(tool_context)
        assert reset_response["status"] == "reset"

    assert PLAN_STATE_KEY not in tool_context.state

    log_messages = [record.getMessage() for record in caplog.records]
    assert any("Stored supervisor plan" in message for message in log_messages)
    assert any("Marked task 1" in message for message in log_messages)
    assert any("Marked task 5" in message for message in log_messages)
    assert any("Supervisor plan state cleared" in message for message in log_messages)
