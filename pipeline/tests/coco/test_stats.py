from dataset_pipeline.coco import CocoDataset
from dataset_pipeline.coco.stats import images_per_category


def test_counts_distinct_images_not_boxes() -> None:
    dataset = CocoDataset.model_validate(
        {
            "info": {"description": "test", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [
                {"id": 1, "file_name": "a.jpg", "width": 100, "height": 100},
                {"id": 2, "file_name": "b.jpg", "width": 100, "height": 100},
            ],
            "categories": [{"id": 1, "name": "car", "supercategory": "none"}],
            "annotations": [
                # 3 cajas de "car" en la misma imagen -> cuenta como 1 imagen
                {
                    "id": i,
                    "image_id": 1,
                    "category_id": 1,
                    "bbox": [0, 0, 10, 10],
                    "area": 100,
                    "iscrowd": 0,
                    "segmentation": [],
                }
                for i in range(1, 4)
            ],
        }
    )

    counts = images_per_category(dataset)

    assert counts == {"car": 1}


def test_declared_category_without_annotations_is_not_counted() -> None:
    # El seed del portal siembra "dog" y "bicycle" aunque nadie los anote: una
    # categoría sin ninguna caja no es una clase del dataset.
    dataset = CocoDataset.model_validate(
        {
            "info": {"description": "test", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [{"id": 1, "file_name": "a.jpg", "width": 100, "height": 100}],
            "categories": [
                {"id": 1, "name": "car", "supercategory": "none"},
                {"id": 2, "name": "dog", "supercategory": "none"},
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
                }
            ],
        }
    )

    assert images_per_category(dataset) == {"car": 1}
