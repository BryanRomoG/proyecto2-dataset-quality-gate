"""Dobles de `copilot.llm.LLMClient` para probar el loop de `copilot.agent`
sin depender de un proveedor real: determinísticos, sin red, sin costo.
"""

from collections import deque

from dataset_pipeline.copilot.llm import LLMTurn


class ScriptedLLMClient:
    """Responde con una secuencia fija de `LLMTurn`, en orden, sin importar
    el contenido del mensaje recibido. `sent_messages` registra lo que le
    llegó, por si un escenario necesita afirmar sobre ello."""

    def __init__(self, turns: list[LLMTurn]):
        self._turns = deque(turns)
        self.sent_messages: list[str] = []
        self.system_prompt: str | None = None

    def start_chat(self, system_prompt: str, tool_methods) -> "ScriptedLLMClient":
        self.system_prompt = system_prompt
        self.tool_methods = tool_methods
        return self

    def send(self, message: str) -> LLMTurn:
        self.sent_messages.append(message)
        return self._turns.popleft()

    def send_tool_result(self, name: str, result: object) -> LLMTurn:
        self.sent_messages.append(f"tool_result:{name}={result!r}")
        return self._turns.popleft()


class RaisingLLMClient:
    """Simula un LLM que no responde (timeout, cuota agotada, 5xx, ...)."""

    def __init__(self, exc: Exception):
        self._exc = exc

    def start_chat(self, system_prompt: str, tool_methods):
        raise self._exc
