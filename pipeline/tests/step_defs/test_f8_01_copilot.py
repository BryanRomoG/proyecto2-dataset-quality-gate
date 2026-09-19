"""Step definitions de features/specs/f8-01-copilot.feature.

SPEC-F8-01 a SPEC-F8-06 (Frente 8, T-3.3, issue #14). Usa
`tests/copilot/fakes.py` (dobles determinísticos de `LLMClient`) para que
el comportamiento del loop de `copilot.agent` se pruebe sin llamar a un
proveedor real -- red, costo y no determinismo cero. La evidencia contra
un LLM real (Gemini, capa gratuita) vive aparte en
`tests/copilot/test_live_gemini_smoke.py`, documentada en `SPECS.md`.
"""

import hashlib
import json
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from copilot.fakes import RaisingLLMClient, ScriptedLLMClient
from dataset_pipeline.copilot.agent import CopilotAnswer, run_copilot_query
from dataset_pipeline.copilot.llm import LLMTurn, ToolCallRequest
from dataset_pipeline.copilot.tools import CopilotToolkit

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f8-01-copilot.feature"
TOOLS_SOURCE = (
    REPO_ROOT / "pipeline" / "src" / "dataset_pipeline" / "copilot" / "tools.py"
).read_text(encoding="utf-8")

scenarios(str(FEATURE_FILE))


@pytest.fixture
def context() -> dict:
    return {}


def _write_data_dir(data_dir: Path, min_images_value: float = 214.0) -> None:
    (data_dir / "quality.json").write_text(
        json.dumps(
            {
                "passed": False,
                "checks": [
                    {
                        "name": "min_images_per_class",
                        "value": min_images_value,
                        "threshold": 300.0,
                        "direction": "gte",
                        "severity": "fail",
                        "passed": min_images_value >= 300.0,
                        "offending_samples": ["car"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "splits.json").write_text(
        json.dumps(
            {
                "seed": 42,
                "ratios": {"train": 0.7, "val": 0.15, "test": 0.15},
                "assignments": {"1": "train"},
                "counts": {"train": 1, "val": 0, "test": 0},
            }
        ),
        encoding="utf-8",
    )
    (data_dir / "versions.json").write_text(
        json.dumps(
            {
                "current": "v0.2.0",
                "releases": [
                    {
                        "version": "v0.2.0",
                        "message": "fixture BDD",
                        "created_at": "2026-09-18T08:00:00Z",
                        "dvc_rev": "abc1234",
                        "diff_vs_previous": None,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


# --- SPEC-F8-01: ninguna herramienta escribe ---


@given("el Copilot con sus cuatro herramientas de solo lectura", target_fixture="context")
def copilot_toolkit(tmp_path: Path) -> dict:
    _write_data_dir(tmp_path)
    return {"toolkit": CopilotToolkit(tmp_path), "data_dir": tmp_path}


def _hash_data_dir(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(data_dir.glob("*.json")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


@when("se invoca cada herramienta disponible")
def invoke_every_tool(context: dict) -> None:
    toolkit: CopilotToolkit = context["toolkit"]
    context["hash_before"] = _hash_data_dir(context["data_dir"])
    toolkit.get_quality_report()
    toolkit.get_split_counts()
    toolkit.list_dataset_versions()
    context["hash_after"] = _hash_data_dir(context["data_dir"])


@then("ningún archivo de datos cambió")
def no_data_file_changed(context: dict) -> None:
    assert context["hash_before"] == context["hash_after"]


@then("el código de las herramientas no contiene ningún patrón de escritura")
def tools_source_has_no_write_pattern() -> None:
    patterns = (
        '"w")',
        "'w')",
        ".write(",
        "os.remove",
        "put_object",
        "INSERT ",
        "UPDATE ",
        "DELETE ",
    )
    for pattern in patterns:
        assert pattern not in TOOLS_SOURCE, pattern


# --- SPEC-F8-02 / SPEC-F8-05: traza visible y versión citada ---


@given(
    "una pregunta que el LLM solo puede responder usando una herramienta",
    target_fixture="context",
)
def question_needing_a_tool(tmp_path: Path) -> dict:
    _write_data_dir(tmp_path)
    llm = ScriptedLLMClient(
        [
            LLMTurn(tool_call=ToolCallRequest(name="get_quality_report", args={}), text=None),
            LLMTurn(tool_call=None, text="La compuerta no pasó: min_images_per_class quedó en 214"),
        ]
    )
    return {
        "toolkit": CopilotToolkit(tmp_path),
        "llm": llm,
        "question": "¿pasó la compuerta de calidad?",
    }


@when("el Copilot responde", target_fixture="context")
def copilot_responds(context: dict) -> dict:
    answer = run_copilot_query(context["question"], context["toolkit"], context["llm"])
    context["answer"] = answer
    return context


@then("la respuesta trae al menos una llamada a herramienta en su traza")
def answer_has_tool_calls(context: dict) -> None:
    answer: CopilotAnswer = context["answer"]
    assert len(answer.tool_calls) >= 1, answer


@then("la traza incluye el nombre de la herramienta y el resultado que devolvió")
def trace_has_name_and_result(context: dict) -> None:
    answer: CopilotAnswer = context["answer"]
    call = answer.tool_calls[0]
    assert call.name == "get_quality_report"
    assert isinstance(call.result, dict)
    assert "checks" in call.result


@then("la respuesta cita la versión actual del dataset")
def answer_cites_version(context: dict) -> None:
    answer: CopilotAnswer = context["answer"]
    assert answer.dataset_version == "v0.2.0"


# --- SPEC-F8-03: la respuesta cambia si cambia la fuente ---


@given("dos fuentes de datos con reportes de calidad distintos", target_fixture="context")
def two_data_sources(tmp_path: Path) -> dict:
    data_dir_a = tmp_path / "a"
    data_dir_b = tmp_path / "b"
    data_dir_a.mkdir()
    data_dir_b.mkdir()
    _write_data_dir(data_dir_a, min_images_value=214.0)
    _write_data_dir(data_dir_b, min_images_value=500.0)
    return {"data_dir_a": data_dir_a, "data_dir_b": data_dir_b}


def _scripted_quality_question() -> ScriptedLLMClient:
    return ScriptedLLMClient(
        [
            LLMTurn(tool_call=ToolCallRequest(name="get_quality_report", args={}), text=None),
            LLMTurn(tool_call=None, text="listo"),
        ]
    )


@when("se hace la misma pregunta contra cada una", target_fixture="context")
def ask_same_question_against_each_source(context: dict) -> dict:
    answer_a = run_copilot_query(
        "¿cuántas imágenes por clase hay?",
        CopilotToolkit(context["data_dir_a"]),
        _scripted_quality_question(),
    )
    answer_b = run_copilot_query(
        "¿cuántas imágenes por clase hay?",
        CopilotToolkit(context["data_dir_b"]),
        _scripted_quality_question(),
    )
    context["answer_a"] = answer_a
    context["answer_b"] = answer_b
    return context


@then("las dos respuestas citan cifras distintas")
def answers_cite_different_figures(context: dict) -> None:
    value_a = context["answer_a"].tool_calls[0].result["checks"][0]["value"]
    value_b = context["answer_b"].tool_calls[0].result["checks"][0]["value"]
    assert value_a != value_b
    assert (value_a, value_b) == (214.0, 500.0)


# --- SPEC-F8-04: admite no saber ---


@given("una pregunta que ninguna herramienta puede responder", target_fixture="context")
def unanswerable_question(tmp_path: Path) -> dict:
    _write_data_dir(tmp_path)
    llm = ScriptedLLMClient(
        [LLMTurn(tool_call=None, text="No lo sé: ninguna de mis herramientas cubre esa pregunta.")]
    )
    return {
        "toolkit": CopilotToolkit(tmp_path),
        "llm": llm,
        "question": "¿cuál es el clima en Guadalajara hoy?",
    }


@then("la respuesta admite que no lo sabe")
def answer_admits_not_knowing(context: dict) -> None:
    answer: CopilotAnswer = context["answer"]
    assert answer.text is not None
    assert "no lo sé" in answer.text.lower() or "no lo se" in answer.text.lower()


@then("no se llamó a ninguna herramienta")
def no_tool_was_called(context: dict) -> None:
    assert context["answer"].tool_calls == []


@then("no cita ninguna versión de dataset")
def no_version_cited(context: dict) -> None:
    assert context["answer"].dataset_version is None


# --- SPEC-F8-06: error del LLM manejado sin traceback ---


@given("un LLM que no responde", target_fixture="context")
def unresponsive_llm(tmp_path: Path) -> dict:
    _write_data_dir(tmp_path)
    return {
        "toolkit": CopilotToolkit(tmp_path),
        "llm": RaisingLLMClient(RuntimeError("Gemini API timeout tras 30s")),
        "question": "¿pasó la compuerta de calidad?",
    }


@then("la respuesta trae un mensaje de error manejado")
def answer_has_handled_error(context: dict) -> None:
    answer: CopilotAnswer = context["answer"]
    assert answer.error is not None
    assert answer.text is None


@then("el mensaje de error no contiene un traceback de Python")
def error_message_has_no_traceback(context: dict) -> None:
    error = context["answer"].error
    assert "Traceback" not in error
    assert 'File "' not in error
