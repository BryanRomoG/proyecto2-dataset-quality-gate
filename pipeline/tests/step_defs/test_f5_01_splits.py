from pathlib import Path

from pytest_bdd import given, scenarios, then, when

from dataset_pipeline.coco import CocoDataset
from dataset_pipeline.splits import generate_stratified_splits

REPO_ROOT = Path(__file__).parents[3]
scenarios(str(REPO_ROOT / "features" / "specs" / "f5-01-splits.feature"))

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


def _dataset_with_n_per_class(n: int) -> CocoDataset:
    images = {i: ["car"] for i in range(1, n + 1)}
    images.update({i: ["person"] for i in range(n + 1, 2 * n + 1)})
    return _dataset(images)


# --- todas las clases presentes en val y test ---


@given("el dataset con ≥300 imágenes por clase", target_fixture="context")
def dataset_with_300_per_class() -> dict:
    return {"dataset": _dataset_with_n_per_class(300)}


@when("se generan los splits con proporciones 0.70/0.15/0.15")
def generate_splits(context: dict) -> None:
    context["result"] = generate_stratified_splits(context["dataset"], RATIOS, seed=42)


@then("las tres particiones suman el total de imágenes")
def splits_sum_to_total(context: dict) -> None:
    total_images = len(context["dataset"].images)
    assert sum(context["result"].counts.values()) == total_images


@then("todas las clases aparecen en train, val y test")
def all_classes_appear_in_all_splits(context: dict) -> None:
    assignments = context["result"].assignments
    car_splits = {split for image_id, split in assignments.items() if image_id <= 300}
    person_splits = {split for image_id, split in assignments.items() if image_id > 300}
    assert car_splits == {"train", "val", "test"}
    assert person_splits == {"train", "val", "test"}


# --- reproducible por semilla ---


@given("seed=42", target_fixture="context")
def seed_42() -> dict:
    return {"dataset": _dataset_with_n_per_class(300), "seed": 42}


@when("se corren los splits dos veces")
def run_splits_twice(context: dict) -> None:
    context["result_a"] = generate_stratified_splits(context["dataset"], RATIOS, context["seed"])
    context["result_b"] = generate_stratified_splits(context["dataset"], RATIOS, context["seed"])


@then("los IDs por split son idénticos (diff vacío)")
def assignments_are_identical(context: dict) -> None:
    assert context["result_a"].assignments == context["result_b"].assignments


# --- cero fuga usando los pares de pHash ---


@given("los pares de near-duplicates detectados en T-202", target_fixture="context")
def duplicate_pairs_from_t202() -> dict:
    dataset = _dataset_with_n_per_class(300)
    # Simula la salida de find_duplicate_pairs (T-2.2): dos fotos de "car"
    # recomprimidas, y una copia que cruza "car"/"person".
    pairs = [(1, 2), (5, 301)]
    return {"dataset": dataset, "pairs": pairs}


@when("se revisa cada par contra la asignación de split")
def check_pairs_against_splits(context: dict) -> None:
    context["result"] = generate_stratified_splits(
        context["dataset"], RATIOS, seed=42, duplicate_pairs=context["pairs"]
    )


@then("ambos elementos del par caen en el mismo split")
def pairs_land_in_same_split(context: dict) -> None:
    assignments = context["result"].assignments
    for image_a, image_b in context["pairs"]:
        assert assignments[image_a] == assignments[image_b]


@then("la intersección de IDs entre train/val/test es vacía")
def splits_are_disjoint(context: dict) -> None:
    assignments = context["result"].assignments
    train_ids = {i for i, split in assignments.items() if split == "train"}
    val_ids = {i for i, split in assignments.items() if split == "val"}
    test_ids = {i for i, split in assignments.items() if split == "test"}
    assert train_ids & val_ids == set()
    assert train_ids & test_ids == set()
    assert val_ids & test_ids == set()
