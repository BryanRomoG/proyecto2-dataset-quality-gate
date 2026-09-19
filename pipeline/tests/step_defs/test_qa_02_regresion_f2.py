"""Step definitions de features/specs/qa-02-regresion-f2.feature.

SPEC-QA-02 (issue #11, T-2.5): confirma que Fase 1 (ingesta Pydantic)
sigue sana con Fase 2 (analizadores + compuerta) encima -- una regresión
real, no una afirmación. El primer escenario corre la suite completa como
subproceso real (`python -m pytest`), el mismo binario pass/fail que ve
GitHub Actions, no una llamada in-process que podría comportarse distinto.
El segundo prueba con el `quality.yaml` real del repo (umbral 300, el del
curso) que la ingesta (T-103) no le presta atención a la compuerta -- son
etapas independientes a propósito.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.coco.loader import load_coco_dataset

REPO_ROOT = Path(__file__).parents[3]
PIPELINE_DIR = REPO_ROOT / "pipeline"
scenarios(str(REPO_ROOT / "features" / "specs" / "qa-02-regresion-f2.feature"))


@pytest.fixture
def context() -> dict:
    return {}


# --- Fase 1 + Fase 2 en verde en la misma corrida ---


@given(
    "la suite completa de Fase 1 (docker, Pydantic) y Fase 2 (analizadores, compuerta)",
    target_fixture="context",
)
def full_suite_context() -> dict:
    return {}


@when("se corren juntas en CI", target_fixture="context")
def run_full_suite(context: dict) -> dict:
    # --ignore de este propio archivo: si no, la suite anidada se incluiría
    # a sí misma y este step recursaría sobre sí mismo sin terminar nunca.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--ignore=tests/step_defs/test_qa_02_regresion_f2.py",
        ],
        cwd=PIPELINE_DIR,
        capture_output=True,
        text=True,
    )
    context["result"] = result
    return context


@then("ambas terminan en verde en la misma corrida")
def suite_is_green(context: dict) -> None:
    result = context["result"]
    assert result.returncode == 0, result.stdout + result.stderr


# --- quality.yaml (umbral real) no rompe la ingesta ---


@given(
    "un dataset COCO válido y quality.yaml con min_images_per_class en 300",
    target_fixture="context",
)
def real_quality_yaml_and_dataset(tmp_path: Path) -> dict:
    policy = yaml.safe_load((REPO_ROOT / "quality.yaml").read_text(encoding="utf-8"))
    assert policy["checks"]["min_images_per_class"]["threshold"] == 300

    coco_dict = {
        "info": {
            "description": "fixture SPEC-QA-02",
            "version": "1.0",
            "date_created": "2026-09-19T00:00:00.000Z",
        },
        "licenses": [],
        "images": [{"id": 1, "file_name": "x.jpg", "width": 10, "height": 10}],
        "annotations": [],
        "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
    }
    coco_path = tmp_path / "dataset.json"
    coco_path.write_text(json.dumps(coco_dict), encoding="utf-8")
    return {"coco_path": coco_path}


@when("se valida el dataset (T-103, ingesta)", target_fixture="context")
def validate_dataset(context: dict) -> dict:
    try:
        context["dataset"] = load_coco_dataset(context["coco_path"])
        context["error"] = None
    except Exception as exc:
        context["error"] = exc
    return context


@then("la validación pasa sin importar el resultado de la compuerta")
def validation_succeeds(context: dict) -> None:
    assert context["error"] is None, context["error"]
