import copy
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from dataset_pipeline.coco import CocoDataset, load_coco_dataset

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def valid_dataset_dict() -> dict:
    return json.loads((FIXTURES / "valid_dataset.json").read_text(encoding="utf-8"))


def test_valid_dataset_parses(valid_dataset_dict: dict) -> None:
    dataset = CocoDataset.model_validate(valid_dataset_dict)

    assert len(dataset.images) == 2
    assert len(dataset.annotations) == 2
    assert len(dataset.categories) == 2


def test_load_coco_dataset_from_file() -> None:
    dataset = load_coco_dataset(FIXTURES / "valid_dataset.json")

    assert isinstance(dataset, CocoDataset)
    assert dataset.categories[0].name == "car"


def test_bbox_with_three_elements_is_rejected(valid_dataset_dict: dict) -> None:
    broken = copy.deepcopy(valid_dataset_dict)
    broken["annotations"][0]["bbox"] = [10, 20, 100]  # falta height

    with pytest.raises(ValidationError) as exc_info:
        CocoDataset.model_validate(broken)

    error_text = str(exc_info.value)
    assert "bbox" in error_text


def test_nonexistent_category_id_is_rejected(valid_dataset_dict: dict) -> None:
    broken = copy.deepcopy(valid_dataset_dict)
    broken["annotations"][0]["category_id"] = 999  # no existe en categories

    with pytest.raises(ValidationError) as exc_info:
        CocoDataset.model_validate(broken)

    error_text = str(exc_info.value)
    assert "category_id" in error_text
    assert "999" in error_text


def test_orphan_image_id_is_rejected(valid_dataset_dict: dict) -> None:
    broken = copy.deepcopy(valid_dataset_dict)
    broken["annotations"][0]["image_id"] = 555  # no existe en images

    with pytest.raises(ValidationError) as exc_info:
        CocoDataset.model_validate(broken)

    error_text = str(exc_info.value)
    assert "image_id" in error_text
    assert "555" in error_text
