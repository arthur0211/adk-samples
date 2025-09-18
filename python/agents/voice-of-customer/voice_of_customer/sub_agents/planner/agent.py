"""Planner agent responsible for generating task lists."""

from google.adk.agents import LlmAgent

from ... import prompt

MODEL = "gemini-2.5-pro"

planner_agent = LlmAgent(
    name="planner_agent",
    model=MODEL,
    description=(
        "Analisa solicitações de Voz do Cliente, coleta requisitos adicionais e "
        "produz planos de trabalho estruturados para o supervisor."
    ),
    instruction=prompt.PLANNER_PROMPT,
    output_key="planner_task_plan",
)
