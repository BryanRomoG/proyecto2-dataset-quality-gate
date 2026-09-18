import pytest

from dataset_pipeline.coco.merge import MergeError, merge_datasets
from dataset_pipeline.coco.models import (
    CocoAnnotation,
    CocoCategory,
    CocoDataset,
    CocoImage,
    CocoInfo,
)


def _dataset(
    *,
    images: list[CocoImage],
    annotations: list[CocoAnnotation],
    categories: list[CocoCategory],
) -> CocoDataset:
    return CocoDataset(
        info=CocoInfo(description="test", version="0.0.0-test", date_created="2026-09-17"),
        licenses=[],
        images=images,
        annotations=annotations,
        categories=categories,
    )


def _image(id: int, file_name: str) -> CocoImage:
    return CocoImage(id=id, file_name=file_name, width=640, height=480)


def _annotation(id: int, image_id: int, category_id: int) -> CocoAnnotation:
    return CocoAnnotation(
        id=id,
        image_id=image_id,
        category_id=category_id,
        bbox=(0, 0, 10, 10),
        area=100,
        iscrowd=0,
        segmentation=[],
    )


def test_merge_two_disjoint_batches_has_no_id_collisions() -> None:
    base = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[_annotation(1, 1, 1)],
        categories=[CocoCategory(id=1, name="car", supercategory="none")],
    )
    incoming = _dataset(
        images=[_image(1, "person-0000.jpg")],
        annotations=[_annotation(1, 1, 1)],
        categories=[CocoCategory(id=1, name="person", supercategory="none")],
    )

    merged = merge_datasets(base, incoming)

    image_ids = [image.id for image in merged.images]
    assert image_ids == sorted(image_ids)
    assert len(set(image_ids)) == len(image_ids)  # sin colisión

    annotation_ids = [annotation.id for annotation in merged.annotations]
    assert len(set(annotation_ids)) == len(annotation_ids)

    file_names = {image.file_name for image in merged.images}
    assert file_names == {"car-0000.jpg", "person-0000.jpg"}

    # la anotación del lote entrante debe seguir apuntando a SU imagen, con
    # el id ya remapeado (no a la imagen del base por accidente).
    incoming_image = next(img for img in merged.images if img.file_name == "person-0000.jpg")
    incoming_annotation = next(
        ann for ann in merged.annotations if ann.image_id == incoming_image.id
    )
    incoming_category = next(
        cat for cat in merged.categories if cat.id == incoming_annotation.category_id
    )
    assert incoming_category.name == "person"


def test_merge_reuses_existing_category_by_name() -> None:
    base = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[_annotation(1, 1, 1)],
        categories=[CocoCategory(id=1, name="car", supercategory="none")],
    )
    incoming = _dataset(
        images=[_image(1, "car-0001.jpg")],
        annotations=[_annotation(1, 1, 5)],
        # mismo nombre "car", pero id=5 en el export del compañero
        categories=[CocoCategory(id=5, name="car", supercategory="none")],
    )

    merged = merge_datasets(base, incoming)

    assert len(merged.categories) == 1
    car_id = merged.categories[0].id
    assert all(ann.category_id == car_id for ann in merged.annotations)


def test_merge_rejects_filename_collision() -> None:
    base = _dataset(
        images=[_image(1, "car-0000.jpg")],
        annotations=[],
        categories=[CocoCategory(id=1, name="car", supercategory="none")],
    )
    incoming = _dataset(
        images=[_image(1, "car-0000.jpg")],  # mismo nombre, imagen distinta
        annotations=[],
        categories=[CocoCategory(id=1, name="car", supercategory="none")],
    )

    with pytest.raises(MergeError) as exc_info:
        merge_datasets(base, incoming)

    assert "car-0000.jpg" in str(exc_info.value)


def test_merge_is_deterministic() -> None:
    base = _dataset(
        images=[_image(1, "car-0000.jpg"), _image(2, "car-0001.jpg")],
        annotations=[_annotation(1, 1, 1), _annotation(2, 2, 1)],
        categories=[CocoCategory(id=1, name="car", supercategory="none")],
    )
    incoming = _dataset(
        images=[_image(3, "person-0000.jpg"), _image(1, "person-0001.jpg")],
        annotations=[_annotation(7, 3, 2), _annotation(2, 1, 2)],
        categories=[CocoCategory(id=2, name="person", supercategory="none")],
    )

    first = merge_datasets(base, incoming)
    second = merge_datasets(base, incoming)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_merge_with_empty_base_only_renumbers_incoming() -> None:
    empty_base = _dataset(images=[], annotations=[], categories=[])
    incoming = _dataset(
        images=[_image(100000, "car-0000.jpg")],
        annotations=[_annotation(1, 100000, 1)],
        categories=[CocoCategory(id=1, name="car", supercategory="none")],
    )

    merged = merge_datasets(empty_base, incoming)

    assert [image.file_name for image in merged.images] == ["car-0000.jpg"]
    assert merged.images[0].id == 1  # renumerado a partir de 0 (base vacío)
    assert merged.annotations[0].id == 1
    assert merged.annotations[0].image_id == merged.images[0].id
