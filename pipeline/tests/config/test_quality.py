from pathlib import Path

import pytest
from pydantic import ValidationError

from dataset_pipeline.config import QualityPolicy, load_quality_policy

FIXTURES = Path(__file__).parent / "fixtures"


def test_valid_quality_policy_loads() -> None:
    policy = load_quality_policy(FIXTURES / "quality.valid.yaml")

    assert policy.checks["min_images_per_class"].threshold == 300
    assert policy.checks["min_images_per_class"].severity == "fail"


def test_missing_min_images_per_class_is_rejected(tmp_path) -> None:
    broken = tmp_path / "quality.yaml"
    broken.write_text(
        "checks:\n  small_objects_ratio:\n    threshold: 0.1\n    severity: warn\n",
        encoding="utf-8",
    )

    with pytest.raises(ValidationError, match="min_images_per_class"):
        load_quality_policy(broken)


def test_invalid_severity_is_rejected() -> None:
    with pytest.raises(ValidationError):
        QualityPolicy.model_validate(
            {"checks": {"min_images_per_class": {"threshold": 300, "severity": "critical"}}}
        )
