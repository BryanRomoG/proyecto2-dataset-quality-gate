"""Step definitions de features/specs/f2-01-modelos-coco.feature (SPEC-F2-01/02).

El caso "valor no numérico" del último escenario también queda cubierto,
con más detalle, en tests/config/test_settings.py — Gherkin no admite dos
Given distintos en un mismo Scenario sin usar Scenario Outline.
"""

import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError
from pytest_bdd import given, parsers, scenarios, then, when

from dataset_pipeline.coco import CocoAnnotation, CocoDataset
from dataset_pipeline.config import PipelineSettings

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f2-01-modelos-coco.feature"
FIXTURES = Path(__file__).parents[1] / "coco" / "fixtures"

scenarios(str(FEATURE_FILE))


@pytest.fixture
def valid_dataset_dict() -> dict:
    return json.loads((FIXTURES / "valid_dataset.json").read_text(encoding="utf-8"))


# `context` no se declara como fixture propia: cada Given de abajo la crea
# vía `target_fixture="context"` y siempre corre primero en su escenario.

# --- bbox con longitud incorrecta ---


@given("un JSON COCO con una anotación cuyo bbox tiene 3 elementos", target_fixture="context")
def annotation_with_short_bbox(valid_dataset_dict: dict) -> dict:
    annotation = copy.deepcopy(valid_dataset_dict["annotations"][0])
    annotation["bbox"] = [10, 20, 100]
    return {"annotation": annotation}


@when("se valida con el modelo Pydantic de Annotation")
def validate_annotation(context: dict) -> None:
    try:
        CocoAnnotation.model_validate(context["annotation"])
        context["error"] = None
    except ValidationError as exc:
        context["error"] = exc


@then("la validación falla")
def validation_fails(context: dict) -> None:
    assert context["error"] is not None


@then(parsers.parse('el error nombra el campo "{field}", no lanza un traceback crudo'))
def error_names_field(context: dict, field: str) -> None:
    assert field in str(context["error"])


# --- category_id / image_id inválidos sobre el dataset completo ---


@given("una anotación con category_id que no existe en categories", target_fixture="context")
def dataset_with_bad_category(valid_dataset_dict: dict) -> dict:
    dataset = copy.deepcopy(valid_dataset_dict)
    dataset["annotations"][0]["category_id"] = 999
    return {"dataset": dataset}


@given("una anotación cuyo image_id no aparece en images", target_fixture="context")
def dataset_with_bad_image(valid_dataset_dict: dict) -> dict:
    dataset = copy.deepcopy(valid_dataset_dict)
    dataset["annotations"][0]["image_id"] = 555
    return {"dataset": dataset}


@when("se valida el COCO completo")
def validate_dataset(context: dict) -> None:
    try:
        CocoDataset.model_validate(context["dataset"])
        context["error"] = None
    except ValidationError as exc:
        context["error"] = exc


@then(parsers.parse('la validación falla nombrando "{field}"'))
def dataset_validation_fails_naming(context: dict, field: str) -> None:
    assert context["error"] is not None
    assert field in str(context["error"])


# --- configuración de entorno inválida ---


@given(
    "un .env sin UPLOAD_MAX_BYTES o con un valor no numérico",
    target_fixture="context",
)
def env_without_upload_max_bytes(monkeypatch) -> dict:
    monkeypatch.delenv("UPLOAD_MAX_BYTES", raising=False)
    return {}


@when("arranca la aplicación")
def start_application(context: dict) -> None:
    try:
        PipelineSettings(_env_file=None)
        context["error"] = None
    except ValidationError as exc:
        context["error"] = exc


@then("falla al inicio con un mensaje claro")
def fails_at_startup(context: dict) -> None:
    assert context["error"] is not None
    assert "upload_max_bytes" in str(context["error"])


@then("no falla más adelante de forma confusa a mitad de un analizador")
def fails_fast_not_later(context: dict) -> None:
    # El assert anterior ya prueba que la falla ocurre en el arranque
    # (al construir PipelineSettings), no en medio de un analizador.
    assert context["error"] is not None
