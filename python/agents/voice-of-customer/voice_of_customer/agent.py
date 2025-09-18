"""Root agent wiring for the Avenue Deep Dive multi-agent system."""

from __future__ import annotations

import datetime

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.adk.tools.agent_tool import AgentTool

from . import prompt
from .sub_agents.data_collector.agent import data_collector_agent
from .sub_agents.planner.agent import planner_agent
from .sub_agents.quali.agent import quali_analyst_agent
from .sub_agents.quant.agent import quanti_analyst_agent
from .sub_agents.reporter.agent import reporter_agent
from .tools import plan_management

MODEL = "gemini-2.5-pro"

supervisor_instruction = prompt.SUPERVISOR_PROMPT.format(
    current_date=datetime.date.today().isoformat()
)

supervisor_agent = LlmAgent(
    name="supervisor_agent",
    model=MODEL,
    description=(
        "Atua como ponto de contato com o usuário e orquestra o fluxo de "
        "agentes especialistas para análises de Voz do Cliente da Avenue."
    ),
    instruction=supervisor_instruction,
    tools=[
        FunctionTool(func=plan_management.store_supervisor_plan),
        FunctionTool(func=plan_management.mark_supervisor_task_completed),
        FunctionTool(func=plan_management.get_supervisor_plan_status),
        FunctionTool(func=plan_management.reset_supervisor_plan),
        AgentTool(agent=planner_agent),
        AgentTool(agent=data_collector_agent),
        AgentTool(agent=quanti_analyst_agent),
        AgentTool(agent=quali_analyst_agent),
        AgentTool(agent=reporter_agent),
    ],
)

root_agent = supervisor_agent

__all__ = ["root_agent", "supervisor_agent"]
