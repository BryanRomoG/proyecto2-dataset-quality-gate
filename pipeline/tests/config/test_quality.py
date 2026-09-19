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


def test_policy_can_be_parsed_from_text() -> None:
    from dataset_pipeline.config.quality import parse_quality_policy

    policy = parse_quality_policy(
        """
checks:
  min_images_per_class:
    threshold: 300
    severity: fail
"""
    )

    assert policy.checks["min_images_per_class"].threshold == 300


def test_policy_from_text_rejects_a_check_without_threshold() -> None:
    from dataset_pipeline.config.quality import parse_quality_policy

    with pytest.raises(ValidationError):
        parse_quality_policy(
            """
checks:
  min_images_per_class:
    severity: fail
"""
        )
