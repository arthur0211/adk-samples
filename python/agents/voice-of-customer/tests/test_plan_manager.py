"""Unit tests for the PlanManager utilities."""

import sys
from pathlib import Path

import pytest

# Ensure the package directory is importable regardless of the working directory
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from voice_of_customer.shared.plan import (  # noqa: E402  # isort: skip
    PLAN_STATE_KEY,
    PlanManager,
    PlanParsingError,
    TaskNotFoundError,
)

PLAN_TEXT = """
Plano gerado pelo planner:
[
    {
        "tasks": [
            {
                "execution_order": 1,
                "task_description": "Validar escopo e coletar requisitos adicionais se necessário.",
                "agent_name": "supervisor_agent",
                "task_completed": false
            },
            {
                "execution_order": 2,
                "task_description": "Consolidar dados históricos de NPS desde 2021.",
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
                "task_description": "Calcular KPIs trimestrais e identificar tendências.",
                "agent_name": "quanti_analyst_agent",
                "task_completed": false
            },
            {
                "execution_order": 4,
                "task_description": "Analisar feedback qualitativo para principais temas.",
                "agent_name": "quali_analyst_agent",
                "task_completed": false
            },
            {
                "execution_order": 5,
                "task_description": "Sintetizar achados em relatório executivo.",
                "agent_name": "reporter_agent",
                "task_completed": false
            }
        ],
        "completed": false
    }
]
"""

INCONSISTENT_PLAN = """
[
    {
        "tasks": [
            {
                "execution_order": 1,
                "task_description": "Verificar briefing inicial.",
                "agent_name": "supervisor_agent",
                "task_completed": true
            },
            {
                "execution_order": 2,
                "task_description": "Levantar métricas quantitativas.",
                "agent_name": "quanti_analyst_agent",
                "task_completed": true
            }
        ],
        "completed": false
    },
    {
        "tasks": [
            {
                "execution_order": 3,
                "task_description": "Classificar sentimentos em feedbacks.",
                "agent_name": "quali_analyst_agent",
                "task_completed": false
            }
        ],
        "completed": true
    }
]
"""

@pytest.fixture
def manager_state() -> tuple[PlanManager, dict]:
    state: dict = {}
    return PlanManager(state), state


def test_set_plan_from_text_stores_plan(manager_state: tuple[PlanManager, dict]) -> None:
    manager, state = manager_state
    plan = manager.set_plan_from_text(PLAN_TEXT)

    assert len(plan) == 2
    assert PLAN_STATE_KEY in state
    assert state[f"{PLAN_STATE_KEY}_raw"].strip().startswith("Plano gerado")

    stored_stage = state[PLAN_STATE_KEY][0]
    assert stored_stage["tasks"][0]["execution_order"] == "1"
    assert stored_stage["tasks"][0]["task_completed"] is False


def test_pending_tasks_and_summary(manager_state: tuple[PlanManager, dict]) -> None:
    manager, _ = manager_state
    manager.set_plan_from_text(PLAN_TEXT)

    pending_orders = [task.execution_order for task in manager.pending_tasks()]
    assert pending_orders == ["1", "2", "3", "4", "5"]

    summary = manager.summary()
    assert summary.total_tasks == 5
    assert summary.completed_tasks == 0
    assert summary.remaining_tasks == 5
    assert summary.total_stages == 2
    assert summary.completed_stages == 0


def test_mark_task_completed_updates_state(manager_state: tuple[PlanManager, dict]) -> None:
    manager, state = manager_state
    manager.set_plan_from_text(PLAN_TEXT)

    manager.mark_task_completed("1")
    assert state[PLAN_STATE_KEY][0]["tasks"][0]["task_completed"] is True
    assert state[PLAN_STATE_KEY][0]["completed"] is False

    manager.mark_task_completed("2")
    assert state[PLAN_STATE_KEY][0]["completed"] is True

    summary = manager.summary()
    assert summary.completed_tasks == 2
    assert summary.remaining_tasks == 3
    assert summary.completed_stages == 1


def test_mark_task_completed_invalid_order_raises(
    manager_state: tuple[PlanManager, dict]
) -> None:
    manager, _ = manager_state
    manager.set_plan_from_text(PLAN_TEXT)

    with pytest.raises(TaskNotFoundError):
        manager.mark_task_completed("99")


def test_invalid_plan_raises_parsing_error(manager_state: tuple[PlanManager, dict]) -> None:
    manager, _ = manager_state

    with pytest.raises(PlanParsingError):
        manager.set_plan_from_text("nenhum json aqui")


def test_reset_plan_clears_state(manager_state: tuple[PlanManager, dict]) -> None:
    manager, state = manager_state
    manager.set_plan_from_text(PLAN_TEXT)

    manager.reset_plan()
    assert PLAN_STATE_KEY not in state
    assert f"{PLAN_STATE_KEY}_raw" not in state

def test_summary_without_plan_returns_zero_metrics(
    manager_state: tuple[PlanManager, dict]
) -> None:
    manager, _ = manager_state

    summary = manager.summary()
    assert summary.total_tasks == 0
    assert summary.completed_tasks == 0
    assert summary.remaining_tasks == 0
    assert summary.total_stages == 0
    assert summary.completed_stages == 0


def test_render_plan_markdown_without_plan(
    manager_state: tuple[PlanManager, dict]
) -> None:
    manager, _ = manager_state

    markdown = manager.render_plan_markdown()
    assert markdown == "Nenhum plano ativo. Acione o planner_agent primeiro."


def test_stage_completion_refreshes_based_on_tasks(
    manager_state: tuple[PlanManager, dict]
) -> None:
    manager, _ = manager_state

    plan = manager.set_plan_from_text(INCONSISTENT_PLAN)
    assert plan[0].completed is True
    assert plan[1].completed is False
