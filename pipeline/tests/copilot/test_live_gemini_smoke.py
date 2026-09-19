"""Evidencia en vivo contra el proveedor real (Gemini, capa gratuita de
Google AI Studio) -- no corre en CI por defecto: se salta si
`GEMINI_API_KEY` no está configurada (marcador `requiere_gemini_api_key`,
ver `pyproject.toml`).

Los escenarios obligatorios de la rúbrica (traza visible, cambia con la
fuente, admite no saber) ya están probados de forma determinística, sin
red ni costo, contra un doble de LLM en
`features/specs/f8-01-copilot.feature`. Esta prueba es la evidencia de que
el mismo loop de `copilot.agent` funciona igual contra el LLM real;
documentada también en `features/specs/SPECS.md`.
"""

from pathlib import Path

import pytest

from dataset_pipeline.copilot.agent import run_copilot_query
from dataset_pipeline.copilot.llm import GeminiClient
from dataset_pipeline.copilot.settings import CopilotSettings
from dataset_pipeline.copilot.tools import CopilotToolkit

REPO_ROOT = Path(__file__).parents[3]
DATA_DIR = REPO_ROOT / "contracts" / "examples"

pytestmark = pytest.mark.requiere_gemini_api_key


@pytest.fixture
def gemini_settings() -> CopilotSettings:
    settings = CopilotSettings()
    if not settings.gemini_api_key:
        pytest.skip("GEMINI_API_KEY no configurada (ver pipeline/.env)")
    return settings


def test_live_query_cites_a_tool_figure_and_the_dataset_version(
    gemini_settings: CopilotSettings,
) -> None:
    toolkit = CopilotToolkit(DATA_DIR)
    llm = GeminiClient(api_key=gemini_settings.gemini_api_key, model=gemini_settings.gemini_model)

    answer = run_copilot_query(
        "¿cuántas imágenes mínimas por clase exige la compuerta, y se cumplió?",
        toolkit,
        llm,
    )

    assert answer.error is None, answer.error
    assert len(answer.tool_calls) >= 1
    assert answer.tool_calls[0].name == "get_quality_report"
    assert answer.dataset_version == "v0.2.0"
    assert answer.text
