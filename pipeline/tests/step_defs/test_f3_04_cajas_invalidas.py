from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.analyzers import analyze_invalid_boxes
from dataset_pipeline.coco import CocoDataset

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f3-04-cajas-invalidas.feature"))


@given(
    "una caja con width negativo y otra con coordenadas fuera de los límites de la imagen",
    target_fixture="context",
)
def dataset_with_two_invalid_boxes() -> dict:
    dataset = CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [{"id": 1, "file_name": "a.jpg", "width": 200, "height": 200}],
            "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [10, 10, -50, 40],  # width negativo
                    "area": 2000,
                    "iscrowd": 0,
                    "segmentation": [],
                },
                {
                    "id": 2,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [150, 150, 100, 100],  # se sale de la imagen 200x200
                    "area": 10000,
                    "iscrowd": 0,
                    "segmentation": [],
                },
            ],
        }
    )
    return {"dataset": dataset}


@when("corre el analizador")
def run_analyzer(context: dict) -> None:
    context["report"] = analyze_invalid_boxes(context["dataset"])


@then("ambas se reportan como inválidas")
def both_are_reported(context: dict) -> None:
    assert len(context["report"].invalid) == 2


@then("se valida que area sea coherente con width*height")
def area_consistency_is_checked(context: dict) -> None:
    negative_width_box = next(
        box for box in context["report"].invalid if box.annotation_id == 1
    )
    # width negativo => width*height también negativo => nunca coincide con
    # un area declarada positiva: el mismo chequeo lo detecta.
    assert "area_inconsistent_with_width_height" in negative_width_box.reasons
