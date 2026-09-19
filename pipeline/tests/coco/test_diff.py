from dataset_pipeline.coco import CocoDataset
from dataset_pipeline.coco.diff import compare_datasets


def _box(ann_id: int, image_id: int, category_id: int, width: float = 100, height: float = 100):
    return {
        "id": ann_id,
        "image_id": image_id,
        "category_id": category_id,
        "bbox": [0, 0, width, height],
        "area": width * height,
        "iscrowd": 0,
        "segmentation": [],
    }


def _dataset(image_ids: list[int], boxes: list[dict]) -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [
                {"id": i, "file_name": f"{i}.jpg", "width": 640, "height": 480} for i in image_ids
            ],
            "categories": [
                {"id": 1, "name": "car", "supercategory": "none"},
                {"id": 2, "name": "person", "supercategory": "none"},
            ],
            "annotations": boxes,
        }
    )


def test_reports_images_and_boxes_added_and_removed() -> None:
    before = _dataset([1, 2], [_box(1, 1, 1), _box(2, 2, 1)])
    after = _dataset([2, 3], [_box(2, 2, 1), _box(3, 3, 1), _box(4, 3, 2)])

    diff = compare_datasets(before, after, min_images_per_class=1)

    assert diff["images_added"] == [3]
    assert diff["images_removed"] == [1]
    assert diff["boxes_added"] == [3, 4]
    assert diff["boxes_removed"] == [1]


def test_classes_below_minimum_are_measured_on_the_new_version() -> None:
    before = _dataset([1, 2], [_box(1, 1, 1), _box(2, 2, 1), _box(3, 1, 2), _box(4, 2, 2)])
    after = _dataset([1, 2], [_box(1, 1, 1), _box(2, 2, 1), _box(3, 1, 2)])

    diff = compare_datasets(before, after, min_images_per_class=2)

    assert diff["images_per_class"] == {"car": 2, "person": 1}
    assert diff["classes_below_minimum"] == ["person"]


def test_reports_classes_that_dropped_out_of_the_minimum() -> None:
    # person estaba en el mínimo (2) y ahora no (1): "salió del mínimo".
    # car ya estaba por debajo en las dos versiones: no es una salida nueva.
    before = _dataset([1, 2, 3], [_box(1, 1, 1), _box(2, 1, 2), _box(3, 2, 2)])
    after = _dataset([1, 2, 3], [_box(1, 1, 1), _box(2, 1, 2)])

    diff = compare_datasets(before, after, min_images_per_class=2)

    assert diff["classes_left_minimum"] == ["person"]


def test_reports_the_change_in_the_small_objects_percentage() -> None:
    # 32x32 = 1024 px de área: 10x10 es pequeño, 100x100 no.
    before = _dataset([1], [_box(1, 1, 1, 100, 100), _box(2, 1, 1, 100, 100)])
    after = _dataset([1], [_box(1, 1, 1, 100, 100), _box(2, 1, 1, 10, 10)])

    diff = compare_datasets(before, after, min_images_per_class=1)

    assert diff["small_objects_pct_before"] == 0.0
    assert diff["small_objects_pct_after"] == 50.0
    assert diff["small_objects_pct_change"] == 50.0


def test_identical_versions_report_no_change() -> None:
    dataset = _dataset([1, 2], [_box(1, 1, 1), _box(2, 2, 2)])

    diff = compare_datasets(dataset, dataset, min_images_per_class=1)

    assert diff["images_added"] == diff["images_removed"] == []
    assert diff["boxes_added"] == diff["boxes_removed"] == []
    assert diff["classes_left_minimum"] == []
    assert diff["small_objects_pct_change"] == 0.0
