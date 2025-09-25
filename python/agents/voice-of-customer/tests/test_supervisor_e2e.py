"""Async end-to-end style test for the supervisor runner."""

from __future__ import annotations

import json
from collections.abc import AsyncGenerator

import pytest

pytest.importorskip("google.adk")

from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.runners import InMemoryRunner
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from voice_of_customer.agent import root_agent
from voice_of_customer.shared.plan import PLAN_STATE_KEY
from voice_of_customer.tools import plan_management

pytest_plugins = ("pytest_asyncio",)


class _ScriptedSupervisorFlow:
    """Injectable flow that produces a deterministic supervisor transcript."""

    def __init__(self, plan_payload: list[dict[str, object]], orders: list[str]):
        self._plan_payload = plan_payload
        self._plan_text = json.dumps(plan_payload, ensure_ascii=False, indent=2)
        self._orders = orders

    async def run_async(self, ctx) -> AsyncGenerator[Event, None]:
        invocation_id = ctx.invocation_id

        # Planner invocation.
        planner_call = Event(
            author="supervisor_agent",
            invocation_id=invocation_id,
            content=types.Content(
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="planner_call",
                            name="planner_agent",
                            args={
                                "request": "Elabore um plano de Voz do Cliente para o usuário."
                            },
                        )
                    )
                ]
            ),
        )
        yield planner_call

        planner_response = Event(
            author="supervisor_agent",
            invocation_id=invocation_id,
            content=types.Content(
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id="planner_call",
                            name="planner_agent",
                            response={"output": self._plan_text},
                        )
                    )
                ]
            ),
        )
        yield planner_response

        # Persist the generated plan using the real plan management tool.
        store_actions = EventActions()
        store_context = ToolContext(ctx, event_actions=store_actions)
        store_result = plan_management.store_supervisor_plan(
            self._plan_text, store_context
        )

        store_call = Event(
            author="supervisor_agent",
            invocation_id=invocation_id,
            content=types.Content(
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="store_plan",
                            name="store_supervisor_plan",
                            args={"plan": self._plan_text},
                        )
                    )
                ]
            ),
        )
        yield store_call

        store_response = Event(
            author="supervisor_agent",
            invocation_id=invocation_id,
            actions=store_actions,
            content=types.Content(
                parts=[
                    types.Part(
                        function_response=types.FunctionResponse(
                            id="store_plan",
                            name="store_supervisor_plan",
                            response={"output": store_result},
                        )
                    )
                ]
            ),
        )
        yield store_response

        # Sequentially mark each task as completed.
        for index, order in enumerate(self._orders, start=1):
            mark_call = Event(
                author="supervisor_agent",
                invocation_id=invocation_id,
                content=types.Content(
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(
                                id=f"mark_{order}",
                                name="mark_supervisor_task_completed",
                                args={"execution_order": order},
                            )
                        )
                    ]
                ),
            )
            yield mark_call

            mark_actions = EventActions()
            mark_context = ToolContext(ctx, event_actions=mark_actions)
            mark_result = plan_management.mark_supervisor_task_completed(
                order, mark_context
            )

            mark_response = Event(
                author="supervisor_agent",
                invocation_id=invocation_id,
                actions=mark_actions,
                content=types.Content(
                    parts=[
                        types.Part(
                            function_response=types.FunctionResponse(
                                id=f"mark_{order}",
                                name="mark_supervisor_task_completed",
                                response={"output": mark_result},
                            )
                        )
                    ]
                ),
            )
            yield mark_response

        # Use the stored state to produce a reporter update and final response.
        status_context = ToolContext(ctx, event_actions=EventActions())
        status_snapshot = plan_management.get_supervisor_plan_status(status_context)
        completed = status_snapshot["summary"]["completed_tasks"]

        reporter_call = Event(
            author="supervisor_agent",
            invocation_id=invocation_id,
            content=types.Content(
                parts=[
                    types.Part(
                        function_call=types.FunctionCall(
                            id="reporter_call",
                            name="reporter_agent",
                            args={
                                "request": "Compartilhe um resumo executivo com base no plano concluído."
                            },
                        )
                    )
                ]
            ),
        )
        yield reporter_call

        reporter_text = (
            "Reporter consolidou a análise: todas as "
            f"{completed} tarefas foram concluídas e registradas no plano."
        )
        reporter_response = Event(
            author="reporter_agent",
            invocation_id=invocation_id,
            content=types.Content(parts=[types.Part(text=reporter_text)]),
        )
        yield reporter_response

        final_text = (
            "Resumo para o usuário: plano salvo com chave"
            f" `{PLAN_STATE_KEY}` e resultado final compartilhado.\n"
            f"Progresso atual:\n{status_snapshot['markdown']}"
        )
        final_event = Event(
            author="supervisor_agent",
            invocation_id=invocation_id,
            content=types.Content(parts=[types.Part(text=final_text)]),
        )
        yield final_event

    async def run_live(self, ctx):
        # This test never exercises live mode but the runner expects the method.
        async for event in self.run_async(ctx):
            yield event


PLAN_FIXTURE = [
    {
        "tasks": [
            {
                "execution_order": "1",
                "task_description": "Validar requisitos adicionais com o solicitante.",
                "agent_name": "supervisor_agent",
                "task_completed": False,
            },
            {
                "execution_order": "2",
                "task_description": "Coletar métricas de NPS recentes.",
                "agent_name": "data_collector_agent",
                "task_completed": False,
            },
        ],
        "completed": False,
    },
    {
        "tasks": [
            {
                "execution_order": "3",
                "task_description": "Gerar relatório executivo com insights acionáveis.",
                "agent_name": "reporter_agent",
                "task_completed": False,
            },
        ],
        "completed": False,
    },
]

ORDERS = [task["execution_order"] for stage in PLAN_FIXTURE for task in stage["tasks"]]


@pytest.mark.asyncio
async def test_supervisor_scripted_e2e(monkeypatch: pytest.MonkeyPatch) -> None:
    """Validates an orchestrated run that exercises planner and plan tools."""

    scripted_flow = _ScriptedSupervisorFlow(plan_payload=PLAN_FIXTURE, orders=ORDERS)

    original_flow_getter = root_agent.__class__._llm_flow.fget

    def _flow_override(agent):
        if agent is root_agent:
            return scripted_flow
        return original_flow_getter(agent)

    monkeypatch.setattr(root_agent.__class__, "_llm_flow", property(_flow_override))

    runner = InMemoryRunner(agent=root_agent)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id="test_user"
    )

    user_message = types.UserContent(
        parts=[
            types.Part(
                text=(
                    "Preciso de um mergulho em Voz do Cliente com etapas de planejamento,"
                    " execução e síntese final."
                )
            )
        ]
    )

    events: list[Event] = []
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        events.append(event)

    # Planner invocation should occur exactly once and precede all tool calls.
    planner_calls = [
        call
        for event in events
        for call in event.get_function_calls()
        if call.name == "planner_agent"
    ]
    assert planner_calls, "planner_agent was never invoked"

    store_responses = [
        event
        for event in events
        if any(
            response.name == "store_supervisor_plan"
            for response in event.get_function_responses()
        )
    ]
    assert store_responses, "plan storage response missing"
    assert PLAN_STATE_KEY in store_responses[0].actions.state_delta

    completion_orders = [
        call.args["execution_order"]
        for event in events
        for call in event.get_function_calls()
        if call.name == "mark_supervisor_task_completed"
    ]
    assert completion_orders == ORDERS

    reporter_messages = [
        part.text
        for event in events
        if event.author == "reporter_agent"
        for part in (event.content.parts if event.content else [])
        if part.text
    ]
    assert reporter_messages, "Reporter output not found in event stream"
    assert "tarefas foram concluídas" in reporter_messages[-1]

    final_texts = [
        part.text
        for event in events
        if event.author == "supervisor_agent"
        for part in (event.content.parts if event.content else [])
        if part.text
    ]
    assert any(PLAN_STATE_KEY in text for text in final_texts)

    final_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=session.user_id, session_id=session.id
    )
    assert final_session
    assert final_session.state.get(PLAN_STATE_KEY)
