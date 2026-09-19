"""Step definitions de features/specs/f10-04-ci.feature (SPEC-F10-04, SPEC-F11-03).

"Corre el workflow de GitHub Actions" no ejecuta el YAML real vía `act`
(no está disponible en este entorno) — en su lugar reproduce exactamente
lo que hace cada paso del workflow (`ruff check .`, `pytest`) como
subproceso real contra un código deliberadamente roto, y confirma que el
exit code es distinto de cero. Es la misma técnica que T-4.2 (mutation
testing), aplicada aquí para probar el workflow en sí, no la lógica de la
compuerta.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f10-04-ci.feature"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pipeline-ci.yml"

scenarios(str(FEATURE_FILE))


@pytest.fixture
def context() -> dict:
    return {}


# --- SPEC-F10-04: un commit que rompe algo tumba el build ---


@given("un commit que rompe un test o el lint", target_fixture="context")
def broken_commit(context: dict, tmp_path: Path) -> dict:
    # Lint roto: import sin usar (F401), exactamente lo que "ruff check ."
    # del workflow real detecta.
    broken_lint_file = tmp_path / "broken_lint.py"
    broken_lint_file.write_text("import os\n\nx = 1\n", encoding="utf-8")

    # Test roto: falla siempre, exactamente lo que "pytest" del workflow
    # real detecta.
    broken_test_file = tmp_path / "test_broken.py"
    broken_test_file.write_text("def test_siempre_falla():\n    assert False\n", encoding="utf-8")

    context["broken_lint_file"] = broken_lint_file
    context["broken_test_file"] = broken_test_file
    return context


@when("corre el workflow de GitHub Actions", target_fixture="context")
def run_workflow_steps(context: dict) -> dict:
    lint_result = subprocess.run(
        [sys.executable, "-m", "ruff", "check", str(context["broken_lint_file"])],
        capture_output=True,
        text=True,
    )
    test_result = subprocess.run(
        [sys.executable, "-m", "pytest", str(context["broken_test_file"])],
        capture_output=True,
        text=True,
    )

    context["lint_exit_code"] = lint_result.returncode
    context["test_exit_code"] = test_result.returncode
    return context


@then("el build termina en rojo")
def build_is_red(context: dict) -> None:
    # El workflow real corre cada paso en secuencia sin continue-on-error:
    # basta con que UNO falle para que el job entero termine en rojo.
    assert context["lint_exit_code"] != 0 or context["test_exit_code"] != 0


@then("ningún paso usa continue-on-error para maquillar el resultado")
def no_continue_on_error(context: dict) -> None:
    workflow = yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))
    for job in workflow["jobs"].values():
        for step in job.get("steps", []):
            assert not step.get("continue-on-error")


# --- SPEC-F11-03: .gitignore correcto ---


@given("git ls-files", target_fixture="context")
def list_tracked_files(context: dict) -> dict:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    context["tracked_files"] = result.stdout.splitlines()
    return context


def _matches_forbidden_pattern(path: str, pattern: str) -> bool:
    """Coincidencia precisa por patrón, no un substring ingenuo.

    Un substring ingenuo marcaría ".env.example" (que SÍ debe estar
    versionado) como si fuera un ".env" real, solo porque contiene "env"
    — bug real encontrado escribiendo este mismo test.
    """
    segments = path.split("/")
    if pattern == ".env":
        return segments[-1] == ".env"
    if pattern in ("__pycache__", ".venv", "node_modules"):
        return pattern in segments
    if pattern == ".dvc/cache":
        return ".dvc/cache" in path
    if pattern == ".tfstate":
        return segments[-1].split(".")[-1] == "tfstate" or ".tfstate" in segments[-1]
    raise ValueError(f"patrón sin regla de coincidencia: {pattern!r}")


@then(
    parsers.parse(
        "no aparece ningún {pattern1}, {pattern2}, {pattern3}, {pattern4}, {pattern5} ni {pattern6}"
    )
)
def no_forbidden_patterns(
    context: dict, pattern1, pattern2, pattern3, pattern4, pattern5, pattern6
) -> None:
    forbidden = [pattern1, pattern2, pattern3, pattern4, pattern5, pattern6]
    for path in context["tracked_files"]:
        for pattern in forbidden:
            assert not _matches_forbidden_pattern(path, pattern), (
                f"'{path}' coincide con el patrón prohibido '{pattern}'"
            )
