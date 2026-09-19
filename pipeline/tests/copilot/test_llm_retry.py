"""`GeminiClient` reintenta con cooldown los errores transitorios del
proveedor (429 cuota agotada, 5xx sobrecarga) -- descubierto en desarrollo
contra la API real (ver SPECS.md, Frente 8). Estas pruebas no llaman a
Gemini: fabrican los mismos errores que devuelve el SDK
(`google.genai.errors`) contra un chat falso, e inyectan una función
`sleep` que no duerme de verdad, así corren en milisegundos.
"""

from google.genai import errors

from dataset_pipeline.copilot.llm import LLMTurn, _GeminiConversation


class _FakeResponse:
    def __init__(self, text: str = "listo"):
        self.function_calls = []
        self.text = text


class _FailThenSucceedChat:
    """Lanza el mismo error transitorio `fail_times` veces y luego responde."""

    def __init__(self, exc_factory, fail_times: int):
        self._exc_factory = exc_factory
        self._fail_times = fail_times
        self.calls = 0

    def send_message(self, message):
        self.calls += 1
        if self.calls <= self._fail_times:
            raise self._exc_factory()
        return _FakeResponse()


def _server_overloaded() -> errors.ServerError:
    return errors.ServerError(
        code=503,
        response_json={"error": {"code": 503, "message": "high demand", "status": "UNAVAILABLE"}},
    )


def _quota_exhausted() -> errors.ClientError:
    return errors.ClientError(
        code=429,
        response_json={"error": {"code": 429, "message": "quota", "status": "RESOURCE_EXHAUSTED"}},
    )


def _model_not_found() -> errors.ClientError:
    return errors.ClientError(
        code=404,
        response_json={"error": {"code": 404, "message": "no existe", "status": "NOT_FOUND"}},
    )


def _conversation(chat, **kwargs) -> _GeminiConversation:
    sleeps: list[float] = kwargs.pop("sleeps", [])
    return _GeminiConversation(
        chat,
        max_retries=kwargs.pop("max_retries", 3),
        base_cooldown_seconds=kwargs.pop("base_cooldown_seconds", 0.0),
        sleep=sleeps.append,
    )


def test_retries_a_503_and_eventually_succeeds() -> None:
    sleeps: list[float] = []
    chat = _FailThenSucceedChat(_server_overloaded, fail_times=2)
    conversation = _conversation(chat, sleeps=sleeps)

    turn = conversation.send("¿pasó la compuerta?")

    assert turn == LLMTurn(tool_call=None, text="listo")
    assert chat.calls == 3
    assert len(sleeps) == 2


def test_retries_a_429_quota_error() -> None:
    chat = _FailThenSucceedChat(_quota_exhausted, fail_times=1)
    conversation = _conversation(chat)

    turn = conversation.send("¿pasó la compuerta?")

    assert turn == LLMTurn(tool_call=None, text="listo")
    assert chat.calls == 2


def test_gives_up_after_max_retries_and_raises_the_original_error() -> None:
    sleeps: list[float] = []
    chat = _FailThenSucceedChat(_server_overloaded, fail_times=999)
    conversation = _conversation(chat, max_retries=2, sleeps=sleeps)

    try:
        conversation.send("¿pasó la compuerta?")
        raise AssertionError("se esperaba que send() lanzara errors.ServerError")
    except errors.ServerError:
        pass

    assert chat.calls == 3  # intento inicial + 2 reintentos
    assert len(sleeps) == 2


def test_does_not_retry_a_non_transient_error() -> None:
    sleeps: list[float] = []
    chat = _FailThenSucceedChat(_model_not_found, fail_times=999)
    conversation = _conversation(chat, sleeps=sleeps)

    try:
        conversation.send("¿pasó la compuerta?")
        raise AssertionError("se esperaba que send() lanzara errors.ClientError")
    except errors.ClientError:
        pass

    assert chat.calls == 1
    assert sleeps == []
