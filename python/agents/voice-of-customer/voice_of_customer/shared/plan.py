"""Utilities for managing planner-generated task lists."""

from __future__ import annotations

import json
from collections.abc import MutableMapping, Sequence
from dataclasses import dataclass, field
from typing import Any

PLAN_STATE_KEY = "supervisor_plan"
RAW_PLAN_STATE_KEY_SUFFIX = "_raw"


class PlanParsingError(ValueError):
    """Raised when the planner output cannot be parsed into a plan."""


class TaskNotFoundError(KeyError):
    """Raised when attempting to update a task that does not exist."""


@dataclass
class PlannerTask:
    """Represents a single task emitted by the planner agent."""

    execution_order: str
    task_description: str
    agent_name: str
    task_completed: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannerTask":
        try:
            execution_order = str(data["execution_order"]).strip()
            task_description = str(data["task_description"]).strip()
            agent_name = str(data["agent_name"]).strip()
        except KeyError as exc:  # pragma: no cover - defensive guard
            raise PlanParsingError("Planner task is missing required fields") from exc

        task_completed = bool(data.get("task_completed", False))
        return cls(
            execution_order=execution_order,
            task_description=task_description,
            agent_name=agent_name,
            task_completed=task_completed,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "execution_order": self.execution_order,
            "task_description": self.task_description,
            "agent_name": self.agent_name,
            "task_completed": self.task_completed,
        }


@dataclass
class PlannerStage:
    """A stage groups together tasks that share a common milestone."""

    tasks: list[PlannerTask] = field(default_factory=list)
    completed: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PlannerStage":
        tasks_data = data.get("tasks", [])
        if not isinstance(tasks_data, list):  # pragma: no cover - validation safety
            raise PlanParsingError("Stage 'tasks' must be a list")
        tasks = [PlannerTask.from_dict(task) for task in tasks_data]
        completed = bool(data.get("completed", False))
        stage = cls(tasks=tasks, completed=completed)
        stage.refresh_completion()
        return stage

    def refresh_completion(self) -> None:
        self.completed = all(task.task_completed for task in self.tasks)
        if not self.tasks:
            self.completed = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "tasks": [task.to_dict() for task in self.tasks],
            "completed": self.completed,
        }


PlanType = list[PlannerStage]


@dataclass
class PlanSummary:
    """Aggregated metrics describing the state of a plan."""

    total_tasks: int
    completed_tasks: int
    remaining_tasks: int
    total_stages: int
    completed_stages: int

    def as_dict(self) -> dict[str, int]:
        return {
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "remaining_tasks": self.remaining_tasks,
            "total_stages": self.total_stages,
            "completed_stages": self.completed_stages,
        }


class PlanManager:
    """Encapsulates all plan management logic for the supervisor agent."""

    def __init__(
        self,
        state: MutableMapping[str, Any],
        plan_state_key: str = PLAN_STATE_KEY,
    ) -> None:
        self._state = state
        self._plan_state_key = plan_state_key
        self._raw_plan_key = f"{plan_state_key}{RAW_PLAN_STATE_KEY_SUFFIX}"

    def set_plan_from_text(self, planner_output: str) -> PlanType:
        plan = self._parse_plan_text(planner_output)
        self._persist_plan(plan, raw_text=planner_output)
        return plan

    def load_plan(self) -> PlanType:
        raw_plan = self._state.get(self._plan_state_key)
        if not raw_plan:
            return []
        plan: list[PlannerStage] = []
        for stage in raw_plan:
            plan.append(PlannerStage.from_dict(dict(stage)))
        return plan

    def reset_plan(self) -> None:
        self._state.pop(self._plan_state_key, None)
        self._state.pop(self._raw_plan_key, None)

    def mark_task_completed(self, execution_order: str) -> PlannerTask:
        plan = self.load_plan()
        if not plan:
            raise PlanParsingError("No plan found in session state.")

        target_order = str(execution_order).strip()
        updated_task: PlannerTask | None = None
        for stage in plan:
            for task in stage.tasks:
                if task.execution_order == target_order:
                    if not task.task_completed:
                        task.task_completed = True
                        stage.refresh_completion()
                    updated_task = task
                    break
            if updated_task:
                break

        if not updated_task:
            raise TaskNotFoundError(
                f"Task with execution_order '{execution_order}' was not found."
            )

        self._persist_plan(plan)
        return updated_task

    def pending_tasks(self) -> list[PlannerTask]:
        tasks: list[PlannerTask] = []
        for stage in self.load_plan():
            tasks.extend(task for task in stage.tasks if not task.task_completed)
        return tasks

    def summary(self) -> PlanSummary:
        plan = self.load_plan()
        total_tasks = sum(len(stage.tasks) for stage in plan)
        completed_tasks = sum(
            1
            for stage in plan
            for task in stage.tasks
            if task.task_completed
        )
        remaining_tasks = total_tasks - completed_tasks
        total_stages = len(plan)
        completed_stages = sum(1 for stage in plan if stage.completed)
        return PlanSummary(
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            remaining_tasks=remaining_tasks,
            total_stages=total_stages,
            completed_stages=completed_stages,
        )

    def plan_as_dict(self) -> list[dict[str, Any]]:
        plan = self.load_plan()
        return [stage.to_dict() for stage in plan]

    def render_plan_markdown(self) -> str:
        plan = self.load_plan()
        if not plan:
            return "Nenhum plano ativo. Acione o planner_agent primeiro."

        lines: list[str] = ["## Plano de tarefas do supervisor"]
        for stage_index, stage in enumerate(plan, start=1):
            status = "✅" if stage.completed else "🕒"
            lines.append(f"### Etapa {stage_index} {status}")
            for task in stage.tasks:
                task_status = "✅" if task.task_completed else "⬜"
                lines.append(
                    f"- {task_status} ({task.execution_order}) "
                    f"[{task.agent_name}] {task.task_description}"
                )
        return "\n".join(lines)

    def _persist_plan(
        self,
        plan: Sequence[PlannerStage],
        *,
        raw_text: str | None = None,
    ) -> None:
        self._state[self._plan_state_key] = [stage.to_dict() for stage in plan]
        if raw_text is not None:
            self._state[self._raw_plan_key] = raw_text

    @staticmethod
    def _parse_plan_text(planner_output: str) -> PlanType:
        try:
            data = json.loads(planner_output)
        except json.JSONDecodeError:
            try:
                payload = PlanManager._extract_first_json_array(planner_output)
                data = json.loads(payload)
            except (ValueError, json.JSONDecodeError) as exc:
                raise PlanParsingError("Planner output is not valid JSON") from exc
        if not isinstance(data, list):
            raise PlanParsingError("Planner output must be a JSON list")

        plan: list[PlannerStage] = []
        for stage in data:
            if not isinstance(stage, dict):
                raise PlanParsingError("Each stage must be a JSON object")
            plan.append(PlannerStage.from_dict(stage))
        return plan

    @staticmethod
    def _extract_first_json_array(text: str) -> str:
        start_index = None
        depth = 0
        for index, char in enumerate(text):
            if char == "[":
                if depth == 0:
                    start_index = index
                depth += 1
            elif char == "]" and depth:
                depth -= 1
                if depth == 0 and start_index is not None:
                    return text[start_index : index + 1]
        raise ValueError("No JSON array found in text")


__all__ = [
    "PLAN_STATE_KEY",
    "PlanManager",
    "PlanParsingError",
    "PlanSummary",
    "PlannerStage",
    "PlannerTask",
    "TaskNotFoundError",
]
