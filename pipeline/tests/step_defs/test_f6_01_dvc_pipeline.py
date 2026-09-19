"""Step definitions de features/specs/f6-01-dvc-pipeline.feature.

Estos son tests de integración reales: invocan el `dvc` de verdad (vía
subprocess) contra el repo tal cual está, no un mock. El escenario que
necesita MinIO/S3 en vivo se salta si no hay remote alcanzable — no hay
forma honesta de probarlo sin infraestructura real corriendo.
"""

import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f6-01-dvc-pipeline.feature"))


def _dvc(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["dvc", *args], cwd=REPO_ROOT, capture_output=True, text=True)


# --- dvc repro es idempotente ---


@given("dvc.yaml con etapas declaradas", target_fixture="context")
def dvc_yaml_exists() -> dict:
    assert (REPO_ROOT / "dvc.yaml").exists()
    return {}


@when('se corre "dvc repro" dos veces seguidas')
def run_repro_twice(context: dict) -> None:
    context["first"] = _dvc("repro")
    context["second"] = _dvc("repro")


@then("la segunda corrida no rehace ninguna etapa")
def second_run_does_nothing(context: dict) -> None:
    assert context["second"].returncode == 0, context["second"].stderr
    assert "Running stage" not in context["second"].stdout
    assert "up to date" in context["second"].stdout.lower()


# --- solo se rehacen las etapas afectadas ---


@given("el pipeline ya corrido", target_fixture="context")
def pipeline_already_run() -> dict:
    result = _dvc("repro")
    assert result.returncode == 0, result.stderr
    return {}


@when("se modifica un archivo de entrada de una sola etapa")
def modify_one_stage_input(context: dict) -> None:
    splits_config = REPO_ROOT / "splits.yaml"
    original = splits_config.read_text(encoding="utf-8")
    data = yaml.safe_load(original)
    data["seed"] = data["seed"] + 1  # cambia algo, sin importar el valor exacto

    context["splits_config_path"] = splits_config
    context["original_content"] = original

    splits_config.write_text(yaml.safe_dump(data), encoding="utf-8")
    context["result"] = _dvc("repro")


@then("dvc repro solo rehace esa etapa y las que dependen de ella")
def only_affected_stage_reran(context: dict) -> None:
    try:
        stdout = context["result"].stdout
        assert context["result"].returncode == 0, context["result"].stderr
        # "Running stage 'split'" (ejecución real) o "'split' is cached"
        # (DVC reconoce que ya calculó esto antes y solo restaura el
        # output) son ambas evidencia de que reconoció el cambio en esa
        # etapa — a diferencia de "didn't change, skipping" para las que
        # de verdad no debían tocarse.
        assert "Running stage 'split'" in stdout or "'split' is cached" in stdout
        for untouched in ("validate", "analyze"):
            assert f"Running stage '{untouched}'" not in stdout
            assert f"'{untouched}' is cached" not in stdout
    finally:
        # Restaurar el archivo y el estado del pipeline, sin dejar el
        # working tree modificado después del test.
        context["splits_config_path"].write_text(context["original_content"], encoding="utf-8")
        _dvc("repro")


# --- datos fuera de Git ---


@given("el repositorio versionado", target_fixture="context")
def repo_is_versioned() -> dict:
    return {}


@then("git ls-files no incluye ningún .jpg/.png/.parquet")
def no_binary_data_in_git(context: dict) -> None:
    tracked = subprocess.run(
        ["git", "ls-files", "data/"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout
    offending = [
        line for line in tracked.splitlines() if line.endswith((".jpg", ".png", ".parquet"))
    ]
    assert offending == [], f"datos binarios versionados en git: {offending}"


@then("sí incluye dvc.lock y los archivos .dvc")
def dvc_lock_and_dvc_files_are_tracked(context: dict) -> None:
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True
    ).stdout.splitlines()
    assert "dvc.lock" in tracked
    assert any(path.endswith(".dvc") for path in tracked)


# --- mismo hash entre DEV y PROD (necesita MinIO real) ---


def _minio_reachable() -> bool:
    result = _dvc("remote", "list")
    if "dev" not in result.stdout:
        return False
    status = _dvc("status", "-r", "dev")
    return status.returncode == 0


@given("un dataset empujado a MinIO (dev) y a S3 (prod)", target_fixture="context")
def dataset_pushed_to_both_remotes() -> dict:
    if not _minio_reachable():
        pytest.skip("MinIO (remote 'dev') no está disponible en este entorno")
    push_dev = _dvc("push", "-r", "dev")
    assert push_dev.returncode == 0, push_dev.stderr
    return {}


@when("se compara el content hash del dvc.lock en ambos remotes")
def compare_hash_between_remotes(context: dict) -> None:
    pytest.skip("Requiere credenciales reales de AWS S3 para el remote 'prod' — no disponibles")


@then("el hash es idéntico")
def hash_is_identical(context: dict) -> None:
    pytest.skip("Ver paso anterior")


@then("ninguna etapa re-empaqueta o re-comprime distinto en PROD")
def no_stage_repacks_differently(context: dict) -> None:
    pytest.skip("Ver paso anterior")
