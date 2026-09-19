from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.coco import CocoDataset
from dataset_pipeline.coco.merge import MergeError, merge_datasets

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f6-02-merge-lotes.feature"))


def _dataset(images: list[dict], annotations: list[dict], categories: list[dict]) -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": images,
            "annotations": annotations,
            "categories": categories,
        }
    )


def _image(id: int, file_name: str) -> dict:
    return {"id": id, "file_name": file_name, "width": 100, "height": 100}


def _annotation(id: int, image_id: int, category_id: int) -> dict:
    return {
        "id": id,
        "image_id": image_id,
        "category_id": category_id,
        "bbox": [0, 0, 10, 10],
        "area": 100,
        "iscrowd": 0,
        "segmentation": [],
    }


# --- fusionar dos lotes disjuntos no produce colisión de ids ---


@given("un dataset base y un lote entrante con ids que se solapan", target_fixture="context")
def base_and_overlapping_incoming() -> dict:
    base = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[_annotation(1, 1, 1)],
        categories=[{"id": 1, "name": "car", "supercategory": "none"}],
    )
    incoming = _dataset(
        images=[_image(1, "person-0000.jpg")],  # mismo id=1, archivo distinto
        annotations=[_annotation(1, 1, 1)],
        categories=[{"id": 1, "name": "person", "supercategory": "none"}],
    )
    return {"base": base, "incoming": incoming}


@when("se fusiona el lote entrante sobre el base")
def merge_incoming_over_base(context: dict) -> None:
    context["result"] = merge_datasets(context["base"], context["incoming"])


@then("ninguna imagen ni anotación del resultado comparte id")
def no_id_collisions(context: dict) -> None:
    merged: CocoDataset = context["result"]
    image_ids = [image.id for image in merged.images]
    annotation_ids = [annotation.id for annotation in merged.annotations]
    assert len(set(image_ids)) == len(image_ids)
    assert len(set(annotation_ids)) == len(annotation_ids)


@then("cada anotación fusionada sigue apuntando a su propia imagen")
def annotations_point_to_their_own_image(context: dict) -> None:
    merged: CocoDataset = context["result"]
    incoming_image = next(img for img in merged.images if img.file_name == "person-0000.jpg")
    incoming_annotation = next(
        ann for ann in merged.annotations if ann.image_id == incoming_image.id
    )
    incoming_category = next(
        cat for cat in merged.categories if cat.id == incoming_annotation.category_id
    )
    assert incoming_category.name == "person"


# --- una categoría con el mismo nombre se reutiliza, no se duplica ---


@given(
    "un lote entrante con una categoría que existe en el base con otro id numérico",
    target_fixture="context",
)
def incoming_reuses_category_name() -> dict:
    base = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[_annotation(1, 1, 1)],
        categories=[{"id": 1, "name": "car", "supercategory": "none"}],
    )
    incoming = _dataset(
        images=[_image(1, "car-0001.jpg")],
        annotations=[_annotation(1, 1, 5)],
        categories=[{"id": 5, "name": "car", "supercategory": "none"}],
    )
    return {"base": base, "incoming": incoming}


@then("el dataset resultante tiene una sola categoría con ese nombre")
def only_one_category_with_that_name(context: dict) -> None:
    merged: CocoDataset = context["result"]
    car_categories = [cat for cat in merged.categories if cat.name == "car"]
    assert len(car_categories) == 1


# --- colisión de nombre de archivo se rechaza ---


@given(
    "un lote entrante con una imagen que usa el mismo file_name que una imagen del base",
    target_fixture="context",
)
def incoming_has_filename_collision() -> dict:
    base = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[],
        categories=[{"id": 1, "name": "car", "supercategory": "none"}],
    )
    incoming = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[],
        categories=[{"id": 1, "name": "car", "supercategory": "none"}],
    )
    return {"base": base, "incoming": incoming}


@when("se intenta fusionar el lote entrante sobre el base")
def try_merge_incoming_over_base(context: dict) -> None:
    try:
        context["result"] = merge_datasets(context["base"], context["incoming"])
    except MergeError as error:
        context["error"] = error


@then("la fusión falla nombrando el archivo en colisión")
def merge_fails_naming_the_file(context: dict) -> None:
    assert "error" in context, "se esperaba un MergeError y la fusión no falló"
    assert "car-0000.jpg" in str(context["error"])


# --- la fusión es reproducible ---


@given("un dataset base y un lote entrante", target_fixture="context")
def base_and_incoming() -> dict:
    base = _dataset(
        images=[_image(1, "car-0000.jpg"), _image(2, "car-0001.jpg")],
        annotations=[_annotation(1, 1, 1), _annotation(2, 2, 1)],
        categories=[{"id": 1, "name": "car", "supercategory": "none"}],
    )
    incoming = _dataset(
        images=[_image(3, "person-0000.jpg"), _image(1, "person-0001.jpg")],
        annotations=[_annotation(7, 3, 2), _annotation(2, 1, 2)],
        categories=[{"id": 2, "name": "person", "supercategory": "none"}],
    )
    return {"base": base, "incoming": incoming}


@when("se fusiona el lote entrante sobre el base dos veces por separado")
def merge_twice(context: dict) -> None:
    context["result_a"] = merge_datasets(context["base"], context["incoming"])
    context["result_b"] = merge_datasets(context["base"], context["incoming"])


@then("ambos resultados son idénticos")
def both_results_are_identical(context: dict) -> None:
    assert context["result_a"].model_dump(mode="json") == context["result_b"].model_dump(
        mode="json"
    )
