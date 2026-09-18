"""Step definitions de features/specs/f4-01-quality-gate.feature.

Texto literal del Gherkin tomado del issue #9 en GitHub (SPEC-F4-01 a
SPEC-F4-04). "Se ejecuta el pipeline"/"se vuelve a correr la compuerta"
invocan el CLI real como subproceso: así el escenario prueba lo mismo que
va a correr el evaluador el día del Control 2 —
`python -m dataset_pipeline.quality_gate.cli ...` con un exit code real
del sistema operativo, no un valor de retorno en memoria.
"""

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f4-01-quality-gate.feature"
PIPELINE_SRC = Path(__file__).parents[2] / "src"

scenarios(str(FEATURE_FILE))


@pytest.fixture
def context() -> dict:
    return {}


def _coco_dict_with_class_count(count: int) -> dict:
    """COCO sintético con una sola categoría y exactamente `count` imágenes
    distintas anotadas con ella, así `min_images_per_class` == count."""
    images = [
        {"id": i, "file_name": f"img-{i}.jpg", "width": 640, "height": 480}
        for i in range(1, count + 1)
    ]
    annotations = [
        {
            "id": i,
            "image_id": i,
            "category_id": 1,
            "bbox": [0, 0, 10, 10],
            "area": 100,
            "iscrowd": 0,
            "segmentation": [],
        }
        for i in range(1, count + 1)
    ]
    return {
        "info": {
            "description": "fixture BDD de la compuerta",
            "version": "1.0",
            "date_created": "2026-09-15T00:00:00.000Z",
        },
        "licenses": [],
        "images": images,
        "annotations": annotations,
        "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
    }


def _source_tree_hash() -> str:
    """Hash de todo el código fuente de quality_gate/, para probar que un
    escenario no lo tocó — la evidencia real de "no se modificó ningún
    archivo de código", no solo una afirmación en el nombre del step."""
    digest = hashlib.sha256()
    quality_gate_dir = PIPELINE_SRC / "dataset_pipeline" / "quality_gate"
    for path in sorted(quality_gate_dir.rglob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _run_cli(coco_dict: dict, policy_dict: dict, tmp_path: Path) -> dict:
    coco_path = tmp_path / "dataset.json"
    coco_path.write_text(json.dumps(coco_dict), encoding="utf-8")

    policy_path = tmp_path / "quality.yaml"
    policy_path.write_text(yaml.dump(policy_dict), encoding="utf-8")

    output_path = tmp_path / "quality.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dataset_pipeline.quality_gate.cli",
            "--coco",
            str(coco_path),
            "--policy",
            str(policy_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
    )

    return {
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "report": json.loads(output_path.read_text(encoding="utf-8")),
    }


# --- SPEC-F4-01: cambiar el YAML cambia el resultado sin tocar código ---


@given(parsers.parse("un quality.yaml con min_images_per_class en {threshold:d}"))
def quality_policy_default_severity(context: dict, threshold: int) -> None:
    context["policy_dict"] = {
        "checks": {"min_images_per_class": {"threshold": threshold, "severity": "fail"}}
    }


@given(parsers.parse("un dataset cuyo min_images_per_class real es {count:d}"))
def dataset_with_count(context: dict, count: int) -> None:
    context["coco_dict"] = _coco_dict_with_class_count(count)


@when("se sube el valor a 100000 y se vuelve a correr la compuerta", target_fixture="context")
def raise_threshold_and_rerun(context: dict, tmp_path: Path) -> dict:
    hash_before = _source_tree_hash()

    context["policy_dict"]["checks"]["min_images_per_class"]["threshold"] = 100_000
    result = _run_cli(context["coco_dict"], context["policy_dict"], tmp_path)

    context.update(result)
    context["source_hash_before"] = hash_before
    context["source_hash_after"] = _source_tree_hash()
    return context


@then("el check ahora falla")
def check_now_fails(context: dict) -> None:
    [check] = context["report"]["checks"]
    assert check["passed"] is False, context["stdout"]


@then("no se modificó ningún archivo de código para lograrlo")
def source_code_untouched(context: dict) -> None:
    assert context["source_hash_before"] == context["source_hash_after"]


# --- SPEC-F4-02 / SPEC-F4-03: severidad fail vs warn ---


@given(
    parsers.parse('un check en severidad "{severity}" que no pasa'),
    target_fixture="context",
)
def check_with_severity_that_fails(context: dict, severity: str) -> dict:
    # threshold=300, dataset con solo 1 imagen -> el check nunca pasa, sea
    # cual sea la severidad.
    context["policy_dict"] = {
        "checks": {"min_images_per_class": {"threshold": 300, "severity": severity}}
    }
    context["coco_dict"] = _coco_dict_with_class_count(1)
    return context


@when("se ejecuta el pipeline", target_fixture="context")
def run_pipeline(context: dict, tmp_path: Path) -> dict:
    result = _run_cli(context["coco_dict"], context["policy_dict"], tmp_path)
    context.update(result)
    return context


@then("el proceso termina con exit code distinto de 0")
def exit_code_nonzero(context: dict) -> None:
    assert context["exit_code"] != 0, context["stdout"]


@then("el proceso continúa")
def process_continues(context: dict) -> None:
    assert context["exit_code"] == 0, context["stdout"]


@then("el warn aparece en quality.json como un check no cumplido")
def warn_appears_as_failed_check(context: dict) -> None:
    [check] = context["report"]["checks"]
    assert check["severity"] == "warn"
    assert check["passed"] is False


# --- SPEC-F4-04: el reporte trae valor vs umbral y muestras ofensoras ---


@given("cualquier check evaluado", target_fixture="context")
def any_evaluated_check(context: dict, tmp_path: Path) -> dict:
    policy_dict = {"checks": {"min_images_per_class": {"threshold": 300, "severity": "fail"}}}
    coco_dict = _coco_dict_with_class_count(1)
    result = _run_cli(coco_dict, policy_dict, tmp_path)
    context.update(result)
    return context


@then("quality.json incluye resultado, valor observado, umbral y muestras ofensoras")
def report_includes_full_evidence(context: dict) -> None:
    [check] = context["report"]["checks"]
    assert "passed" in check
    assert "value" in check
    assert "threshold" in check
    assert "offending_samples" in check


@then("no es solo un booleano true/false")
def report_is_not_just_a_boolean(context: dict) -> None:
    [check] = context["report"]["checks"]
    assert set(check.keys()) > {"passed"}
    assert check["value"] != check["passed"]
