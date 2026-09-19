import json

import numpy as np
import pytest
from PIL import Image

from dataset_pipeline.coco.embedding import build_embedding, image_features, project_pca
from dataset_pipeline.coco.models import CocoDataset


def _dataset() -> CocoDataset:
    return CocoDataset.model_validate(
        {
            "info": {"description": "t", "version": "0", "date_created": "2026-01-01"},
            "licenses": [],
            "categories": [
                {"id": 1, "name": "car", "supercategory": "none"},
                {"id": 2, "name": "person", "supercategory": "none"},
            ],
            "images": [
                {"id": i, "file_name": f"{i}.jpg", "width": 20, "height": 20} for i in (1, 2, 3, 4)
            ],
            "annotations": [
                {
                    "id": 100 + i,
                    "image_id": i,
                    "category_id": 1 if i <= 2 else 2,
                    "bbox": [0, 0, 5, 5],
                    "area": 25,
                    "iscrowd": 0,
                    "segmentation": [],
                }
                for i in (1, 2, 3, 4)
            ],
        }
    )


def _solid(color: tuple[int, int, int]) -> Image.Image:
    return Image.new("RGB", (32, 32), color)


def test_image_features_has_fixed_length_and_range() -> None:
    features = image_features(_solid((10, 200, 30)))

    assert features.shape == (8 * 8 * 3 + 16 * 3,)
    assert features.min() >= 0.0
    assert features.max() <= 1.0


def test_similar_images_are_closer_than_different_ones() -> None:
    dark_a = image_features(_solid((10, 10, 10)))
    dark_b = image_features(_solid((14, 12, 10)))
    bright = image_features(_solid((250, 240, 245)))

    assert np.linalg.norm(dark_a - dark_b) < np.linalg.norm(dark_a - bright)


def test_pca_projects_to_two_components_and_reports_variance() -> None:
    rng = np.random.default_rng(0)
    # Una dirección domina la varianza: el primer componente debe explicarla.
    data = rng.normal(size=(50, 5)) * np.array([10.0, 1.0, 0.5, 0.1, 0.1])

    coordinates, explained = project_pca(data)

    assert coordinates.shape == (50, 2)
    assert explained[0] > 0.9
    assert explained[0] >= explained[1]
    assert sum(explained) <= 1.0 + 1e-9


def test_pca_is_deterministic_and_sign_stable() -> None:
    data = np.random.default_rng(1).normal(size=(30, 6))

    first, _ = project_pca(data)
    second, _ = project_pca(data.copy())

    assert np.array_equal(first, second)


def test_pca_first_axis_carries_the_largest_spread() -> None:
    data = np.random.default_rng(2).normal(size=(40, 4)) * np.array([5.0, 1.0, 1.0, 1.0])

    coordinates, _ = project_pca(data)

    assert coordinates[:, 0].std() > coordinates[:, 1].std()


@pytest.mark.parametrize("rows", [0, 1])
def test_pca_with_too_few_samples_returns_zeros_not_nan(rows: int) -> None:
    coordinates, explained = project_pca(np.ones((rows, 4)))

    assert coordinates.shape == (rows, 2)
    assert not np.isnan(coordinates).any()
    assert explained == [0.0, 0.0]


def test_pca_with_constant_features_returns_zeros_not_nan() -> None:
    coordinates, explained = project_pca(np.full((5, 4), 0.3))

    assert not np.isnan(coordinates).any()
    assert explained == [0.0, 0.0]


def test_build_embedding_keeps_class_split_and_skips_images_without_features() -> None:
    dataset = _dataset()
    rng = np.random.default_rng(3)
    features = {1: rng.random(6), 2: rng.random(6), 3: rng.random(6)}  # la 4 no se materializó

    artifact = build_embedding(dataset, features, split_by_image={1: "train", 3: "val"})

    assert artifact["method"] == "pca"
    assert [point["image_id"] for point in artifact["points"]] == [1, 2, 3]
    by_id = {point["image_id"]: point for point in artifact["points"]}
    assert by_id[1]["categories"] == ["car"]
    assert by_id[3]["categories"] == ["person"]
    assert by_id[1]["split"] == "train"
    assert by_id[2]["split"] is None


def test_build_embedding_is_valid_strict_json() -> None:
    dataset = _dataset()
    artifact = build_embedding(dataset, {1: np.zeros(6)})  # una sola imagen: sin varianza

    # allow_nan=False: un NaN en el artefacto rompería JSON.parse en el server.
    json.dumps(artifact, allow_nan=False)
