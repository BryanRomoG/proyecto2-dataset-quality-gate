"""Orquesta una pregunta contra el LLM + las herramientas de solo lectura
del Copilot (T-3.3, issue #14): SPEC-F8-02 a SPEC-F8-05.

El loop vive aquí y no en `llm.py` ni en `tools.py` porque es la única
pieza que conoce a la vez las reglas de negocio del ticket: cada respuesta
que usó al menos una herramienta cita su traza completa de llamadas
(SPEC-F8-02) y la versión actual del dataset (SPEC-F8-05) -- la versión se
lee aquí directamente de `toolkit.current_version()`, nunca se confía en
que el texto generado por el LLM la mencione correctamente. Un error del
LLM (de red, de cuota, lo que sea) se atrapa aquí y nunca sale como
traceback (SPEC-F8-05). Y "no sé" es una respuesta válida sin tool calls
(SPEC-F8-04): si no se usó ninguna herramienta, no hay versión que citar.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from dataset_pipeline.copilot.llm import LLMClient
from dataset_pipeline.copilot.tools import CopilotToolkit

SYSTEM_PROMPT = (
    "Eres el Dataset Copilot de un pipeline de MLOps. Respondes preguntas "
    "sobre la calidad, los splits y las versiones del dataset usando "
    "exclusivamente las herramientas de solo lectura que tienes disponibles. "
    "Nunca inventes una cifra: toda cifra que menciones debe venir del "
    "resultado de una herramienta. Si la pregunta no se puede responder con "
    "las herramientas disponibles, dilo explícitamente ('no lo sé' o "
    "equivalente) en vez de adivinar o suponer."
)

MAX_TOOL_CALLS = 5

_TOOL_NAMES = (
    "get_quality_report",
    "get_split_counts",
    "list_dataset_versions",
    "get_version_diff",
)


class CopilotError(Exception):
    """Errores propios del loop del Copilot (no del proveedor del LLM)."""


@dataclass(frozen=True)
class ToolCallRecord:
    name: str
    args: dict
    result: object


@dataclass(frozen=True)
class CopilotAnswer:
    text: str | None
    tool_calls: list[ToolCallRecord]
    dataset_version: str | None
    error: str | None


def _tool_methods(toolkit: CopilotToolkit) -> list[Callable]:
    return [getattr(toolkit, name) for name in _TOOL_NAMES]


def run_copilot_query(question: str, toolkit: CopilotToolkit, llm: LLMClient) -> CopilotAnswer:
    trace: list[ToolCallRecord] = []

    try:
        conversation = llm.start_chat(SYSTEM_PROMPT, _tool_methods(toolkit))
        turn = conversation.send(question)

        for _ in range(MAX_TOOL_CALLS):
            if turn.tool_call is None:
                break
            if turn.tool_call.name not in _TOOL_NAMES:
                raise CopilotError(
                    f"el LLM pidió una herramienta desconocida: {turn.tool_call.name}"
                )
            method = getattr(toolkit, turn.tool_call.name)
            result = method(**turn.tool_call.args)
            trace.append(
                ToolCallRecord(name=turn.tool_call.name, args=turn.tool_call.args, result=result)
            )
            turn = conversation.send_tool_result(turn.tool_call.name, result)
        else:
            raise CopilotError(f"el LLM pidió más de {MAX_TOOL_CALLS} herramientas seguidas")
    except Exception as exc:
        return CopilotAnswer(
            text=None,
            tool_calls=trace,
            dataset_version=None,
            error=f"El Copilot no pudo responder ({type(exc).__name__}): {exc}",
        )

    dataset_version = toolkit.current_version() if trace else None
    return CopilotAnswer(
        text=turn.text, tool_calls=trace, dataset_version=dataset_version, error=None
    )
