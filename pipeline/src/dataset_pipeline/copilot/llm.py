"""Cliente del LLM para el Dataset Copilot (T-3.3, issue #14).

Abstrae "hablar con un LLM que puede pedir herramientas" detrás de
`LLMConversation`/`LLMClient`, para que `copilot.agent` (el loop que arma
la traza y decide cuándo parar) se pueda probar sin llamar a un proveedor
real. La única implementación real es `GeminiClient` (capa gratuita de
Google AI Studio, ver `GEMINI_API_KEY` en `.env`); los tests usan un doble
programado (`tests/copilot/fakes.py`).

Function calling manual (`automatic_function_calling.disable=True`): así
`agent.py` controla el loop y puede armar la traza exacta de qué
herramienta se llamó con qué argumentos y qué devolvió -- si se dejara el
function calling automático del SDK, esa traza quedaría oculta dentro del
cliente y SPEC-F8-02 (traza visible) no se podría probar.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ToolCallRequest:
    name: str
    args: dict


@dataclass(frozen=True)
class LLMTurn:
    """Una respuesta del LLM: o pide una herramienta, o da texto final -- nunca ambas."""

    tool_call: ToolCallRequest | None
    text: str | None

    def __post_init__(self) -> None:
        if (self.tool_call is None) == (self.text is None):
            raise ValueError("LLMTurn debe traer exactamente uno de tool_call o text")


class LLMConversation(Protocol):
    def send(self, message: str) -> LLMTurn: ...
    def send_tool_result(self, name: str, result: object) -> LLMTurn: ...


class LLMClient(Protocol):
    def start_chat(self, system_prompt: str, tool_methods: list[Callable]) -> LLMConversation: ...


class GeminiClient:
    """Implementación real sobre la capa gratuita de la API de Gemini."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        from google import genai

        self._genai_client = genai.Client(api_key=api_key)
        self._model = model

    def start_chat(self, system_prompt: str, tool_methods: list[Callable]) -> LLMConversation:
        from google.genai import types

        declarations = [
            types.FunctionDeclaration.from_callable_with_api_option(
                callable=fn, api_option="GEMINI_API"
            )
            for fn in tool_methods
        ]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            tools=[types.Tool(function_declarations=declarations)],
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
        chat = self._genai_client.chats.create(model=self._model, config=config)
        return _GeminiConversation(chat)


class _GeminiConversation:
    def __init__(self, chat):
        self._chat = chat

    def send(self, message: str) -> LLMTurn:
        return self._turn_from_response(self._chat.send_message(message))

    def send_tool_result(self, name: str, result: object) -> LLMTurn:
        from google.genai import types

        part = types.Part.from_function_response(name=name, response={"result": result})
        return self._turn_from_response(self._chat.send_message(part))

    def _turn_from_response(self, response) -> LLMTurn:
        calls = response.function_calls
        if calls:
            call = calls[0]
            return LLMTurn(
                tool_call=ToolCallRequest(name=call.name, args=dict(call.args or {})), text=None
            )
        return LLMTurn(tool_call=None, text=response.text or "")
