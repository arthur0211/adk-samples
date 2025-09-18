"""Qualitative analyst agent."""

from google.adk.agents import LlmAgent

from ... import prompt

MODEL = "gemini-2.5-pro"

quali_analyst_agent = LlmAgent(
    name="quali_analyst_agent",
    model=MODEL,
    description=(
        "Sintetiza percepções qualitativas da Voz do Cliente e identifica "
        "insights acionáveis sobre experiências e jornadas."
    ),
    instruction=prompt.QUALI_ANALYST_PROMPT,
)
