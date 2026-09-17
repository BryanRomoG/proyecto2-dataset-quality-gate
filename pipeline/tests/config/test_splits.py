from pathlib import Path

import pytest
from pydantic import ValidationError

from dataset_pipeline.config import SplitsConfig, load_splits_config

FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_splits_config_loads() -> None:
    config = load_splits_config(FIXTURES / "splits.valid.yaml")

    assert config.seed == 42
    assert config.ratios["train"] == 0.7


def test_ratios_not_summing_to_one_is_rejected() -> None:
    with pytest.raises(ValidationError, match="deben sumar 1.0"):
        SplitsConfig.model_validate(
            {"seed": 42, "ratios": {"train": 0.5, "val": 0.2, "test": 0.2}}
        )


def test_missing_split_is_rejected() -> None:
    with pytest.raises(ValidationError, match="faltan"):
        SplitsConfig.model_validate({"seed": 42, "ratios": {"train": 0.85, "val": 0.15}})
