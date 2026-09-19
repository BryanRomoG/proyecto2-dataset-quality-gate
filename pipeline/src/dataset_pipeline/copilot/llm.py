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

`GeminiClient` reintenta con cooldown (backoff exponencial + jitter) los
errores que el propio proveedor marca como transitorios -- 429 (cuota
agotada) y 5xx (sobrecarga, mantenimiento). Se descubrió en desarrollo que
esto pasa de verdad en la capa gratuita bajo carga (ver SPECS.md); un 404
(modelo inexistente) o 400 (API key inválida) nunca se reintenta, porque
reintentarlo no lo arregla, solo tarda más en fallar.
"""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, TypeVar

_T = TypeVar("_T")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_DEFAULT_MAX_RETRIES = 3
_DEFAULT_BASE_COOLDOWN_SECONDS = 2.0


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


def _is_retryable(exc: Exception) -> bool:
    from google.genai import errors

    return isinstance(exc, errors.APIError) and exc.code in _RETRYABLE_STATUS_CODES


def _call_with_cooldown(
    call: Callable[[], _T],
    *,
    max_retries: int,
    base_cooldown_seconds: float,
    sleep: Callable[[float], None],
) -> _T:
    attempt = 0
    while True:
        try:
            return call()
        except Exception as exc:
            if attempt >= max_retries or not _is_retryable(exc):
                raise
            cooldown = base_cooldown_seconds * (2**attempt) + random.uniform(0, 1)
            sleep(cooldown)
            attempt += 1


class GeminiClient:
    """Implementación real sobre la capa gratuita de la API de Gemini."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-3.5-flash-lite",
        max_retries: int = _DEFAULT_MAX_RETRIES,
        base_cooldown_seconds: float = _DEFAULT_BASE_COOLDOWN_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ):
        from google import genai

        self._genai_client = genai.Client(api_key=api_key)
        self._model = model
        self._max_retries = max_retries
        self._base_cooldown_seconds = base_cooldown_seconds
        self._sleep = sleep

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
        return _GeminiConversation(
            chat,
            max_retries=self._max_retries,
            base_cooldown_seconds=self._base_cooldown_seconds,
            sleep=self._sleep,
        )


class _GeminiConversation:
    def __init__(
        self,
        chat,
        *,
        max_retries: int,
        base_cooldown_seconds: float,
        sleep: Callable[[float], None],
    ):
        self._chat = chat
        self._max_retries = max_retries
        self._base_cooldown_seconds = base_cooldown_seconds
        self._sleep = sleep

    def send(self, message: str) -> LLMTurn:
        return self._turn_from_response(self._send_with_cooldown(message))

    def send_tool_result(self, name: str, result: object) -> LLMTurn:
        from google.genai import types

        part = types.Part.from_function_response(name=name, response={"result": result})
        return self._turn_from_response(self._send_with_cooldown(part))

    def _send_with_cooldown(self, message):
        return _call_with_cooldown(
            lambda: self._chat.send_message(message),
            max_retries=self._max_retries,
            base_cooldown_seconds=self._base_cooldown_seconds,
            sleep=self._sleep,
        )

    def _turn_from_response(self, response) -> LLMTurn:
        calls = response.function_calls
        if calls:
            call = calls[0]
            return LLMTurn(
                tool_call=ToolCallRequest(name=call.name, args=dict(call.args or {})), text=None
            )
        return LLMTurn(tool_call=None, text=response.text or "")
