"""Quantitative analyst agent."""

from google.adk.agents import LlmAgent

from ... import prompt

MODEL = "gemini-2.5-pro"

quanti_analyst_agent = LlmAgent(
    name="quanti_analyst_agent",
    model=MODEL,
    description=(
        "Transforma dados estruturados de Voz do Cliente em KPIs e análises "
        "estatísticas que direcionam decisões de produto e atendimento."
    ),
    instruction=prompt.QUANTI_ANALYST_PROMPT,
)
