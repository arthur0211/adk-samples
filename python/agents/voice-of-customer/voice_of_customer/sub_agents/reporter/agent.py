"""Reporter agent responsible for final synthesis."""

from google.adk.agents import LlmAgent

from ... import prompt

MODEL = "gemini-2.5-pro"

reporter_agent = LlmAgent(
    name="reporter_agent",
    model=MODEL,
    description=(
        "Entrega relatórios finais claros e acionáveis para stakeholders da "
        "Avenue com base em análises quantitativas e qualitativas."
    ),
    instruction=prompt.REPORTER_PROMPT,
)
