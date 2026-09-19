"""Step definitions de features/specs/f6-01-dvc-pipeline.feature.

Estos son tests de integración reales: invocan el `dvc` de verdad (vía
subprocess) contra el repo tal cual está, no un mock. El escenario que
necesita MinIO (DEV) y S3 (PROD) en vivo se salta si alguno no es alcanzable
(sin MinIO, sin credenciales de AWS o sin el dato crudo): no hay forma
honesta de probarlo sin infraestructura real corriendo.
"""

import hashlib
import subprocess
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f6-01-dvc-pipeline.feature"))


def _dvc(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["dvc", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def _raw_data_available() -> bool:
    """`dvc repro` necesita el dato crudo real en disco, no solo el
    puntero `.dvc` -- en un checkout limpio (CI, o cualquier clon nuevo)
    nadie corrió `dvc pull` todavía, así que este archivo no existe."""
    return (REPO_ROOT / "data" / "raw" / "coco.json").exists()


# --- dvc repro es idempotente ---


@given("dvc.yaml con etapas declaradas", target_fixture="context")
def dvc_yaml_exists() -> dict:
    assert (REPO_ROOT / "dvc.yaml").exists()
    if not _raw_data_available():
        pytest.skip("data/raw/coco.json no está en disco -- corre 'dvc pull' primero")
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
    if not _raw_data_available():
        pytest.skip("data/raw/coco.json no está en disco -- corre 'dvc pull' primero")
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


# --- mismo hash entre DEV y PROD (necesita MinIO y S3 reales) ---
#
# DVC direcciona cada objeto por su md5, así que "el mismo content hash en
# DEV y en PROD" equivale a que los dos remotes tengan EXACTAMENTE los objetos
# que nombran los punteros de Git (`.dvc` y `dvc.lock`). `dvc status -c -r X`
# compara esos hashes contra el remote X. La prueba no sube nada: verifica.


def _cloud_status(remote: str) -> subprocess.CompletedProcess | None:
    """`dvc status -c -r <remote>`, o None si el remote no es alcanzable
    (no existe, sin MinIO, sin credenciales de AWS...)."""
    if remote not in _dvc("remote", "list").stdout:
        return None
    result = _dvc("status", "-c", "-r", remote)
    if result.returncode != 0 or "ERROR" in result.stderr:
        return None
    return result


def _md5_of_pointer(pointer: str) -> str:
    """md5 que Git tiene registrado para un dato (`data/raw/*.dvc`)."""
    return yaml.safe_load((REPO_ROOT / pointer).read_text(encoding="utf-8"))["outs"][0]["md5"]


@given("un dataset empujado a MinIO (dev) y a S3 (prod)", target_fixture="context")
def dataset_pushed_to_both_remotes() -> dict:
    if not _raw_data_available():
        pytest.skip("data/raw/coco.json no está en disco -- corre 'dvc pull' primero")
    context: dict = {}
    for remote, donde in (("dev", "MinIO"), ("prod", "S3 (¿credenciales de AWS?)")):
        status = _cloud_status(remote)
        if status is None:
            pytest.skip(f"el remote '{remote}' ({donde}) no está disponible en este entorno")
        context[remote] = status
    return context


@when("se compara el content hash del dvc.lock en ambos remotes")
def compare_hash_between_remotes(context: dict) -> None:
    # Una sola consulta por remote (ya hecha arriba): dvc status -c es lento.
    context["in_sync"] = {remote: "in sync" in context[remote].stdout for remote in ("dev", "prod")}


@then("el hash es idéntico")
def hash_is_identical(context: dict) -> None:
    # Cada remote contiene todos los objetos que nombra el workspace (los
    # punteros de Git): mismos hashes en los dos lados, ninguno "new"/"missing".
    for remote in ("dev", "prod"):
        assert context["in_sync"][remote], (
            f"el remote '{remote}' no está al día con los punteros: {context[remote].stdout}"
        )
    lock = yaml.safe_load((REPO_ROOT / "dvc.lock").read_text(encoding="utf-8"))
    assert lock["stages"], "dvc.lock no declara etapas"


@then("ninguna etapa re-empaqueta o re-comprime distinto en PROD")
def no_stage_repacks_differently(context: dict) -> None:
    # Direccionado por contenido: el objeto guardado bajo el md5 del puntero
    # es byte a byte el archivo local. Si alguien lo re-comprimiera, el md5 del
    # archivo dejaría de coincidir con el que Git tiene registrado.
    local_md5 = hashlib.md5((REPO_ROOT / "data" / "raw" / "coco.json").read_bytes()).hexdigest()
    assert local_md5 == _md5_of_pointer("data/raw/coco.json.dvc")
