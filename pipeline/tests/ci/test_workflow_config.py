"""Frente 10 (T-4.3, issue #19) — el workflow de CI del pipeline Python no
maquilla resultados.

"Ningún paso usa continue-on-error para maquillar el resultado" (AC del
issue #19) se prueba de forma estática, parseando el YAML real que GitHub
Actions va a ejecutar — no basta con decir en un commit message que no se
usa, si alguien lo agrega después este test lo atrapa.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).parents[3]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "pipeline-ci.yml"


def _load_workflow() -> dict:
    return yaml.safe_load(WORKFLOW_PATH.read_text(encoding="utf-8"))


def test_el_workflow_existe():
    assert WORKFLOW_PATH.exists(), f"No existe {WORKFLOW_PATH}"


def test_ningun_paso_usa_continue_on_error():
    workflow = _load_workflow()

    offending_steps: list[str] = []
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            if step.get("continue-on-error"):
                offending_steps.append(f"{job_name}::{step.get('name', step.get('run', '?'))}")

    assert offending_steps == [], (
        f"Estos pasos usan continue-on-error (maquillan el resultado): {offending_steps}"
    )


def test_corre_en_push_y_pull_request_a_main():
    workflow = _load_workflow()
    # YAML parsea la clave "on" como booleano True en YAML 1.1 si no se
    # cita — confirma que el archivo real la escribe como string "on".
    triggers = workflow.get("on") or workflow.get(True)
    assert triggers is not None, "El workflow no define disparadores (on:)"
    assert "push" in triggers
    assert "pull_request" in triggers
    assert triggers["push"]["branches"] == ["main"]


def test_incluye_ruff_check_y_ruff_format_check():
    workflow = _load_workflow()
    run_commands = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "run" in step
    ]
    combined = "\n".join(run_commands)

    assert "ruff check" in combined
    assert "ruff format --check" in combined


def test_incluye_pytest():
    workflow = _load_workflow()
    run_commands = [
        step["run"]
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if "run" in step
    ]
    assert any("pytest" in cmd for cmd in run_commands)
