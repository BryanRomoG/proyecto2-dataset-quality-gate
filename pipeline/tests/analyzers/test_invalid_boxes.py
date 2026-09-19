from dataset_pipeline.analyzers import analyze_invalid_boxes
from dataset_pipeline.coco import CocoDataset


def _dataset(annotations: list[dict]) -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "test", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [{"id": 1, "file_name": "a.jpg", "width": 200, "height": 200}],
            "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
            "annotations": annotations,
        }
    )


def test_negative_width_is_detected() -> None:
    dataset = _dataset(
        [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [10, 10, -50, 40],
                "area": 2000,
                "iscrowd": 0,
                "segmentation": [],
            }
        ]
    )

    report = analyze_invalid_boxes(dataset)

    assert report.total_annotations == 1
    assert len(report.invalid) == 1
    assert "negative_width" in report.invalid[0].reasons


def test_box_out_of_image_bounds_is_detected() -> None:
    dataset = _dataset(
        [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [150, 150, 100, 100],  # se sale de la imagen de 200x200
                "area": 10000,
                "iscrowd": 0,
                "segmentation": [],
            }
        ]
    )

    report = analyze_invalid_boxes(dataset)

    assert "out_of_image_bounds" in report.invalid[0].reasons


def test_area_inconsistent_with_width_height_is_detected() -> None:
    dataset = _dataset(
        [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [10, 10, 50, 40],  # area real = 2000
                "area": 999999,
                "iscrowd": 0,
                "segmentation": [],
            }
        ]
    )

    report = analyze_invalid_boxes(dataset)

    assert "area_inconsistent_with_width_height" in report.invalid[0].reasons


def test_valid_box_is_not_reported() -> None:
    dataset = _dataset(
        [
            {
                "id": 1,
                "image_id": 1,
                "category_id": 1,
                "bbox": [10, 10, 50, 40],
                "area": 2000,
                "iscrowd": 0,
                "segmentation": [],
            }
        ]
    )

    report = analyze_invalid_boxes(dataset)

    assert report.invalid == []


def _box(bbox: list[float], area: float) -> dict:
    return {
        "id": 1,
        "image_id": 1,
        "category_id": 1,
        "bbox": bbox,
        "area": area,
        "iscrowd": 0,
        "segmentation": [],
    }


def test_zero_width_is_detected() -> None:
    # area = 0 es coherente con 0*40, así que solo el ancho cero la delata.
    report = analyze_invalid_boxes(_dataset([_box([10, 10, 0, 40], area=0)]))

    assert len(report.invalid) == 1
    assert report.invalid[0].reasons == ["zero_width"]


def test_zero_height_is_detected() -> None:
    report = analyze_invalid_boxes(_dataset([_box([10, 10, 40, 0], area=0)]))

    assert len(report.invalid) == 1
    assert report.invalid[0].reasons == ["zero_height"]


def test_width_just_below_zero_is_negative() -> None:
    # Frontera: -1 ya es negativo (una mutación `< -1` lo dejaba pasar).
    report = analyze_invalid_boxes(_dataset([_box([10, 10, -1, 40], area=-40)]))

    assert len(report.invalid) == 1
    assert report.invalid[0].reasons == ["negative_width"]


def test_height_just_below_zero_is_negative() -> None:
    report = analyze_invalid_boxes(_dataset([_box([10, 10, 40, -1], area=-40)]))

    assert len(report.invalid) == 1
    assert report.invalid[0].reasons == ["negative_height"]


def test_smallest_positive_box_is_valid() -> None:
    # Frontera del otro lado: 1x1 no es degenerada.
    report = analyze_invalid_boxes(_dataset([_box([10, 10, 1, 1], area=1)]))

    assert report.invalid == []
