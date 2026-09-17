from dataset_pipeline.coco import CocoDataset
from dataset_pipeline.splits import generate_stratified_splits

RATIOS = {"train": 0.70, "val": 0.15, "test": 0.15}


def _dataset(images_with_categories: dict[int, list[str]]) -> CocoDataset:
    category_names = sorted({name for names in images_with_categories.values() for name in names})
    category_ids = {name: i + 1 for i, name in enumerate(category_names)}

    annotations = []
    ann_id = 1
    for image_id, names in images_with_categories.items():
        for name in names:
            annotations.append(
                {
                    "id": ann_id,
                    "image_id": image_id,
                    "category_id": category_ids[name],
                    "bbox": [0, 0, 10, 10],
                    "area": 100,
                    "iscrowd": 0,
                    "segmentation": [],
                }
            )
            ann_id += 1

    return CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "1.0", "date_created": "2026-01-01"},
            "licenses": [],
            "images": [
                {"id": image_id, "file_name": f"{image_id}.jpg", "width": 100, "height": 100}
                for image_id in images_with_categories
            ],
            "categories": [
                {"id": category_id, "name": name, "supercategory": "none"}
                for name, category_id in category_ids.items()
            ],
            "annotations": annotations,
        }
    )


def _dataset_with_20_per_class() -> CocoDataset:
    images = {i: ["car"] for i in range(1, 21)}
    images.update({i: ["person"] for i in range(21, 41)})
    return _dataset(images)


def test_all_classes_appear_in_train_val_and_test() -> None:
    dataset = _dataset_with_20_per_class()

    result = generate_stratified_splits(dataset, RATIOS, seed=42)

    assert sum(result.counts.values()) == 40
    assert set(result.counts) == {"train", "val", "test"}
    assert all(count > 0 for count in result.counts.values())

    car_splits = {result.assignments[i] for i in range(1, 21)}
    person_splits = {result.assignments[i] for i in range(21, 41)}
    assert car_splits == {"train", "val", "test"}
    assert person_splits == {"train", "val", "test"}


def test_reproducible_with_same_seed() -> None:
    dataset = _dataset_with_20_per_class()

    result_a = generate_stratified_splits(dataset, RATIOS, seed=42)
    result_b = generate_stratified_splits(dataset, RATIOS, seed=42)

    assert result_a.assignments == result_b.assignments


def test_different_seed_can_change_assignment() -> None:
    dataset = _dataset_with_20_per_class()

    result_a = generate_stratified_splits(dataset, RATIOS, seed=42)
    result_b = generate_stratified_splits(dataset, RATIOS, seed=7)

    assert result_a.assignments != result_b.assignments


def test_missing_ratio_key_raises() -> None:
    dataset = _dataset_with_20_per_class()

    try:
        generate_stratified_splits(dataset, {"train": 0.8, "val": 0.2}, seed=42)
        raise AssertionError("debía lanzar ValueError")
    except ValueError as exc:
        assert "test" in str(exc)


def test_zero_leakage_duplicate_pairs_stay_in_same_split() -> None:
    dataset = _dataset_with_20_per_class()
    # 1 y 2 son la misma foto (recomprimida); 5 y 21 también, cruzando clases.
    duplicate_pairs = [(1, 2), (5, 21)]

    result = generate_stratified_splits(dataset, RATIOS, seed=42, duplicate_pairs=duplicate_pairs)

    # Verificado par por par, no solo confiando en un conteo agregado.
    for image_a, image_b in duplicate_pairs:
        assert result.assignments[image_a] == result.assignments[image_b]

    train_ids = {i for i, split in result.assignments.items() if split == "train"}
    val_ids = {i for i, split in result.assignments.items() if split == "val"}
    test_ids = {i for i, split in result.assignments.items() if split == "test"}
    assert train_ids & val_ids == set()
    assert train_ids & test_ids == set()
    assert val_ids & test_ids == set()
