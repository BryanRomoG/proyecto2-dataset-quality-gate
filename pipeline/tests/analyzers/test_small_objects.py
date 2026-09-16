from dataset_pipeline.analyzers import analyze_small_objects
from dataset_pipeline.coco import CocoDataset


def _dataset(bboxes: list[tuple[float, float, float, float]]) -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "test", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [{"id": 1, "file_name": "a.jpg", "width": 1000, "height": 1000}],
            "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
            "annotations": [
                {
                    "id": i + 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": list(bbox),
                    "area": bbox[2] * bbox[3],
                    "iscrowd": 0,
                    "segmentation": [],
                }
                for i, bbox in enumerate(bboxes)
            ],
        }
    )


def test_reports_percentage_and_samples_below_threshold() -> None:
    dataset = _dataset([(0, 0, 10, 10), (0, 0, 500, 500)])  # 1 pequeña, 1 grande

    report = analyze_small_objects(dataset, threshold_px=32)

    assert report.total_annotations == 2
    assert report.small_count == 1
    assert report.percentage_below_threshold == 50.0
    assert report.offending_sample_ids == [1]


def test_changing_threshold_in_config_changes_the_result() -> None:
    dataset = _dataset([(0, 0, 40, 40)])

    report_strict = analyze_small_objects(dataset, threshold_px=32)
    report_loose = analyze_small_objects(dataset, threshold_px=64)

    assert report_strict.small_count == 0
    assert report_loose.small_count == 1


def test_most_affected_category() -> None:
    dataset = CocoDataset.model_validate(
        {
            "info": {"description": "test", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [{"id": 1, "file_name": "a.jpg", "width": 1000, "height": 1000}],
            "categories": [
                {"id": 1, "name": "car", "supercategory": "none"},
                {"id": 2, "name": "person", "supercategory": "none"},
            ],
            "annotations": [
                {
                    "id": 1,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [0, 0, 10, 10],
                    "area": 100,
                    "iscrowd": 0,
                    "segmentation": [],
                },
                {
                    "id": 2,
                    "image_id": 1,
                    "category_id": 2,
                    "bbox": [0, 0, 500, 500],
                    "area": 250000,
                    "iscrowd": 0,
                    "segmentation": [],
                },
            ],
        }
    )

    report = analyze_small_objects(dataset, threshold_px=32)

    assert report.most_affected_category == "car"
