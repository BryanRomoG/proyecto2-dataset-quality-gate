from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.analyzers import analyze_small_objects
from dataset_pipeline.coco import CocoDataset

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f3-01-objetos-pequenos.feature"))


def _dataset() -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [{"id": 1, "file_name": "a.jpg", "width": 1000, "height": 1000}],
            "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [0, 0, 10, 10],  # pequeña
                    "area": 100,
                    "iscrowd": 0,
                    "segmentation": [],
                },
                {
                    "id": 2,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [0, 0, 500, 500],  # grande
                    "area": 250000,
                    "iscrowd": 0,
                    "segmentation": [],
                },
            ],
        }
    )


@given(
    "un COCO con cajas de distintos tamaños y un umbral de 32x32 en config",
    target_fixture="context",
)
def dataset_with_threshold() -> dict:
    return {"dataset": _dataset(), "threshold_px": 32}


@when("corre el analizador")
def run_analyzer(context: dict) -> None:
    context["report"] = analyze_small_objects(context["dataset"], context["threshold_px"])


@then("reporta % de objetos bajo el umbral, clase más afectada y muestras ofensoras")
def report_has_expected_fields(context: dict) -> None:
    report = context["report"]
    assert report.percentage_below_threshold == 50.0
    assert report.most_affected_category == "car"
    assert report.offending_sample_ids == [1]


@then("cambiar el umbral en config cambia el resultado sin tocar código")
def changing_threshold_changes_result(context: dict) -> None:
    looser_report = analyze_small_objects(context["dataset"], threshold_px=600)
    assert looser_report.small_count != context["report"].small_count
