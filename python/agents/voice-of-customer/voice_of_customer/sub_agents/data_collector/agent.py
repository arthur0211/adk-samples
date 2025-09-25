"""Agent that focuses on collecting anonymised customer voice datasets."""

from google.adk.agents import LlmAgent

from ... import prompt

MODEL = "gemini-2.5-pro"


def _description() -> str:
    return (
        "Executa buscas internas e externas para reunir dados anonimizados de Voz "
        "do Cliente, preparando insumos para análises quantitativas e "
        "qualitativas."
    )


data_collector_agent = LlmAgent(
    name="data_collector_agent",
    model=MODEL,
    description=_description(),
    instruction=prompt.DATA_COLLECTOR_PROMPT,
)
