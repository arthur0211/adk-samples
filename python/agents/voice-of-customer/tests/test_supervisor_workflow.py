"""Integration-style tests that emulate supervisor workflow interactions."""

import logging
import sys
import textwrap
from pathlib import Path

import pytest

# Ensure package imports work regardless of the working directory used by pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_of_customer.shared.plan import (  # noqa: E402  # isort: skip
    PLAN_STATE_KEY,
    PlanManager,
)


PLANNER_RESPONSE = textwrap.dedent(
    """
    [
        {
            "tasks": [
                {
                    "execution_order": 1,
                    "task_description": "Confirmar escopo com o solicitante e anotar requisitos extras.",
                    "agent_name": "supervisor_agent",
                    "task_completed": false
                },
                {
                    "execution_order": 2,
                    "task_description": "Reunir métricas de NPS e CSAT dos últimos 12 meses.",
                    "agent_name": "data_collector_agent",
                    "task_completed": false
                }
            ],
            "completed": false
        },
        {
            "tasks": [
                {
                    "execution_order": 3,
                    "task_description": "Calcular tendências trimestrais e destacar variações relevantes.",
                    "agent_name": "quanti_analyst_agent",
                    "task_completed": false
                },
                {
                    "execution_order": 4,
                    "task_description": "Identificar temas recorrentes nos feedbacks qualitativos.",
                    "agent_name": "quali_analyst_agent",
                    "task_completed": false
                },
                {
                    "execution_order": 5,
                    "task_description": "Construir síntese executiva com recomendações de próximos passos.",
                    "agent_name": "reporter_agent",
                    "task_completed": false
                }
            ],
            "completed": false
        }
    ]
    """
)


def test_supervisor_interaction_logs_and_status(caplog: pytest.LogCaptureFixture) -> None:
    """Simula uma interação de usuário acompanhando o to-do do supervisor."""

    state: dict = {}
    manager = PlanManager(state)

    with caplog.at_level(logging.INFO):
        plan = manager.set_plan_from_text(PLANNER_RESPONSE)
        # Supervisor conclui as duas primeiras etapas do plano.
        manager.mark_task_completed("1")
        manager.mark_task_completed("2")
        summary = manager.summary()
        markdown = manager.render_plan_markdown()
        manager.reset_plan()

    # O plano inicial possui duas etapas com cinco tarefas no total.
    assert len(plan) == 2
    assert summary.total_tasks == 5
    assert summary.completed_tasks == 2
    assert summary.remaining_tasks == 3
    assert summary.completed_stages == 1

    # A representação em Markdown deve refletir o progresso do supervisor.
    assert "### Etapa 1 ✅" in markdown
    assert "### Etapa 2 🕒" in markdown
    assert "- ✅ (1) [supervisor_agent]" in markdown
    assert "- ✅ (2) [data_collector_agent]" in markdown

    # Após o reset, o estado compartilhado não deve conter mais o plano.
    assert PLAN_STATE_KEY not in state
    assert manager.load_plan() == []

    log_messages = [record.getMessage() for record in caplog.records]
    assert any("Stored supervisor plan" in message for message in log_messages)
    assert any("Marked task 1" in message for message in log_messages)
    assert any("Marked task 2" in message for message in log_messages)
    assert any("Supervisor plan state cleared" in message for message in log_messages)
