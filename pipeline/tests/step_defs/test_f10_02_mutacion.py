"""Step definitions de features/specs/f10-02-mutacion.feature (SPEC-F10-02).

Prueba de mutación manual real, no simbólica: escribe bytes mutados de
verdad en el archivo fuente, corre pytest como subproceso real contra él,
y SIEMPRE restaura el original en un `finally` — incluso si el propio
assert de "pytest pasa a rojo" falla, el archivo nunca debe quedar
mutado en disco. La restauración se verifica dos veces: comparando el
contenido byte a byte, y con `git diff --quiet` (para detectar cualquier
diferencia real contra lo que ya está committeado, no solo contra la
copia en memoria de este test).

PYTHONDONTWRITEBYTECODE=1 en los subprocesos: mutar y restaurar el mismo
archivo dos veces en la misma corrida puede caer dentro de la resolución
de un segundo del reloj, y el chequeo de mtime de Python para invalidar
`__pycache__/*.pyc` no lo detecta — se puede terminar ejecutando
bytecode cacheado de la versión mutada incluso después de restaurar el
.py. Encontrado de verdad haciendo esta misma prueba a mano antes de
escribir este comentario (ver evidencia del issue #18), no es
una precaución teórica.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f10-02-mutacion.feature"
PIPELINE_ROOT = REPO_ROOT / "pipeline"
PIPELINE_SRC = PIPELINE_ROOT / "src"

EVALUATOR_PATH = PIPELINE_SRC / "dataset_pipeline" / "quality_gate" / "evaluator.py"
INVALID_BOXES_PATH = PIPELINE_SRC / "dataset_pipeline" / "analyzers" / "invalid_boxes.py"

scenarios(str(FEATURE_FILE))


@pytest.fixture
def context() -> dict:
    return {}


def _run_pytest(test_path_rel: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-p", "no:cacheprovider", test_path_rel],
        cwd=PIPELINE_ROOT,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )


def _assert_file_restored(path: Path, original: str) -> None:
    assert path.read_text(encoding="utf-8") == original, (
        f"{path} no coincide byte a byte con el original tras restaurar"
    )
    result = subprocess.run(
        ["git", "diff", "--quiet", "--", str(path.relative_to(REPO_ROOT))],
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, (
        f"{path} sigue mostrando diferencias contra git tras restaurar "
        "(working tree no quedó limpio)"
    )


# --- Escenario 1: invertir el comparador de la compuerta ---


@given("la compuerta de calidad con su comparador correcto", target_fixture="context")
def gate_with_correct_comparator(context: dict) -> dict:
    original = EVALUATOR_PATH.read_text(encoding="utf-8")
    assert "return value >= threshold" in original, (
        "no se encontró el comparador esperado en evaluator.py — "
        "¿cambió la implementación desde que se escribió este test?"
    )
    context["original_evaluator"] = original
    context["before_result"] = _run_pytest("tests/quality_gate/test_evaluator.py")
    return context


@when("se invierte el comparador deliberadamente", target_fixture="context")
def invert_comparator(context: dict) -> dict:
    original = context["original_evaluator"]
    mutated = original.replace("return value >= threshold", "return value < threshold")
    assert mutated != original, "la mutación no cambió nada — el reemplazo no encontró su blanco"

    try:
        EVALUATOR_PATH.write_text(mutated, encoding="utf-8")
        context["after_result"] = _run_pytest("tests/quality_gate/test_evaluator.py")
    finally:
        EVALUATOR_PATH.write_text(original, encoding="utf-8")
    return context


@then("pytest pasa a rojo")
def pytest_turns_red(context: dict) -> None:
    assert context["before_result"].returncode == 0, (
        f"la suite ya estaba en rojo ANTES de mutar nada:\n{context['before_result'].stdout}"
    )
    assert context["after_result"].returncode != 0, (
        f"la suite siguió en verde después de invertir el comparador — "
        f"esto NO debería pasar:\n{context['after_result'].stdout}"
    )


@then("el código se restaura después de la prueba")
def code_is_restored_after_scenario_1(context: dict) -> None:
    _assert_file_restored(EVALUATOR_PATH, context["original_evaluator"])


# --- Escenario 2: romper el cálculo de área de las cajas ---


@given("el cálculo de area = width * height", target_fixture="context")
def area_calculation(context: dict) -> dict:
    original = INVALID_BOXES_PATH.read_text(encoding="utf-8")
    assert "expected_area = width * height" in original, (
        "no se encontró el cálculo esperado en invalid_boxes.py — "
        "¿cambió la implementación desde que se escribió este test?"
    )
    context["original_invalid_boxes"] = original
    context["before_result"] = _run_pytest("tests/analyzers/test_invalid_boxes.py")
    return context


@when("se rompe deliberadamente", target_fixture="context")
def break_area_calculation(context: dict) -> dict:
    original = context["original_invalid_boxes"]
    mutated = original.replace("expected_area = width * height", "expected_area = width + height")
    assert mutated != original, "la mutación no cambió nada — el reemplazo no encontró su blanco"

    try:
        INVALID_BOXES_PATH.write_text(mutated, encoding="utf-8")
        context["after_result"] = _run_pytest("tests/analyzers/test_invalid_boxes.py")
    finally:
        INVALID_BOXES_PATH.write_text(original, encoding="utf-8")
    return context


@then("los tests relacionados fallan")
def related_tests_fail(context: dict) -> None:
    assert context["before_result"].returncode == 0, (
        f"la suite ya estaba en rojo ANTES de mutar nada:\n{context['before_result'].stdout}"
    )
    assert context["after_result"].returncode != 0, (
        f"la suite siguió en verde tras romper el cálculo de área — "
        f"esto NO debería pasar:\n{context['after_result'].stdout}"
    )


@then("se restaura el código original")
def code_is_restored_after_scenario_2(context: dict) -> None:
    _assert_file_restored(INVALID_BOXES_PATH, context["original_invalid_boxes"])
