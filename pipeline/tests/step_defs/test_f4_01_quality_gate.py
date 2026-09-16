"""Step definitions de features/specs/f4-01-quality-gate.feature (SPEC-F4-01/02).

"Se corre la compuerta" invoca el CLI real como subproceso (no una llamada
en memoria): así el escenario prueba lo mismo que va a correr el evaluador
el día del Control 2 — `python -m dataset_pipeline.quality_gate.cli ...` y
un código de salida real del sistema operativo.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, parsers, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f4-01-quality-gate.feature"

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


# --- Given ---


@given(parsers.parse("un dataset cuyo min_images_per_class real es {count:d}"))
def dataset_with_count(context: dict, count: int) -> None:
    context["coco_dict"] = _coco_dict_with_class_count(count)


@given(
    parsers.parse(
        'un quality.yaml con min_images_per_class en {threshold:d} y severidad "{severity}"'
    )
)
def quality_policy(context: dict, threshold: int, severity: str) -> None:
    context["policy_dict"] = {
        "checks": {"min_images_per_class": {"threshold": threshold, "severity": severity}}
    }


# --- When ---


@when("se corre la compuerta")
def run_gate(context: dict, tmp_path: Path) -> None:
    coco_path = tmp_path / "dataset.json"
    coco_path.write_text(json.dumps(context["coco_dict"]), encoding="utf-8")

    policy_path = tmp_path / "quality.yaml"
    policy_path.write_text(yaml.dump(context["policy_dict"]), encoding="utf-8")

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

    context["exit_code"] = result.returncode
    context["stdout"] = result.stdout
    context["report"] = json.loads(output_path.read_text(encoding="utf-8"))


# --- Then ---


@then("el reporte queda marcado como aprobado")
def report_passed(context: dict) -> None:
    assert context["report"]["passed"] is True, context["stdout"]


@then("el reporte queda marcado como no aprobado")
def report_not_passed(context: dict) -> None:
    assert context["report"]["passed"] is False, context["stdout"]


@then("el check individual queda marcado como no cumplido")
def individual_check_failed(context: dict) -> None:
    [check] = context["report"]["checks"]
    assert check["passed"] is False


@then("el proceso termina con un código de salida distinto de cero")
def exit_code_nonzero(context: dict) -> None:
    assert context["exit_code"] != 0


@then(parsers.parse("el proceso termina con código de salida {code:d}"))
def exit_code_equals(context: dict, code: int) -> None:
    assert context["exit_code"] == code
