import pytest

from dataset_pipeline.coco import CocoDataset
from dataset_pipeline.coco.filter import UnknownCategoryError, drop_categories
from dataset_pipeline.coco.stats import images_per_category


def _annotation(ann_id: int, image_id: int, category_id: int) -> dict:
    return {
        "id": ann_id,
        "image_id": image_id,
        "category_id": category_id,
        "bbox": [0, 0, 10, 10],
        "area": 100,
        "iscrowd": 0,
        "segmentation": [],
    }


def _dataset() -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "test", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [
                {"id": 1, "file_name": "a.jpg", "width": 100, "height": 100},
                {"id": 2, "file_name": "b.jpg", "width": 100, "height": 100},
                {"id": 3, "file_name": "c.jpg", "width": 100, "height": 100},
            ],
            "categories": [
                {"id": 1, "name": "car", "supercategory": "none"},
                {"id": 2, "name": "person", "supercategory": "none"},
                {"id": 4, "name": "bicycle", "supercategory": "none"},
            ],
            "annotations": [
                _annotation(1, image_id=1, category_id=1),
                _annotation(2, image_id=1, category_id=4),  # bicicleta junto a un carro
                _annotation(3, image_id=2, category_id=2),
                _annotation(4, image_id=3, category_id=4),  # imagen SOLO con bicicleta
            ],
        }
    )


def test_drops_the_category_and_only_its_annotations() -> None:
    result = drop_categories(_dataset(), ["bicycle"])

    assert [category.name for category in result.categories] == ["car", "person"]
    assert [annotation.id for annotation in result.annotations] == [1, 3]


def test_keeps_every_image_even_if_it_only_had_the_dropped_category() -> None:
    result = drop_categories(_dataset(), ["bicycle"])

    assert [image.id for image in result.images] == [1, 2, 3]


def test_ids_of_what_remains_are_not_renumbered() -> None:
    # Renumerar rompería la trazabilidad contra el portal y contra los splits.
    result = drop_categories(_dataset(), ["bicycle"])

    assert {category.id for category in result.categories} == {1, 2}
    assert {annotation.category_id for annotation in result.annotations} <= {1, 2}


def test_result_is_a_valid_dataset_with_the_expected_class_counts() -> None:
    result = drop_categories(_dataset(), ["bicycle"])

    # Se revalida al construirlo: ninguna anotación queda apuntando a la
    # categoría eliminada.
    CocoDataset.model_validate(result.model_dump(mode="json"))
    assert images_per_category(result) == {"car": 1, "person": 1}


def test_does_not_mutate_the_input_dataset() -> None:
    original = _dataset()

    drop_categories(original, ["bicycle"])

    assert len(original.categories) == 3
    assert len(original.annotations) == 4


def test_unknown_category_fails_loudly_instead_of_doing_nothing() -> None:
    with pytest.raises(UnknownCategoryError) as exc_info:
        drop_categories(_dataset(), ["bicicleta"])  # mal escrito

    assert "bicicleta" in str(exc_info.value)


def test_dropping_nothing_returns_an_equal_dataset() -> None:
    original = _dataset()

    assert drop_categories(original, []) == original
