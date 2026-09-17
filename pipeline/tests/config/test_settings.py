import pytest
from pydantic import ValidationError

from dataset_pipeline.config import PipelineSettings


def test_missing_upload_max_bytes_fails_fast(monkeypatch) -> None:
    monkeypatch.delenv("UPLOAD_MAX_BYTES", raising=False)

    with pytest.raises(ValidationError, match="upload_max_bytes"):
        PipelineSettings(_env_file=None)


def test_non_numeric_upload_max_bytes_fails_fast(monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "not-a-number")

    with pytest.raises(ValidationError, match="upload_max_bytes"):
        PipelineSettings(_env_file=None)


def test_valid_upload_max_bytes_loads(monkeypatch) -> None:
    monkeypatch.setenv("UPLOAD_MAX_BYTES", "5242880")

    settings = PipelineSettings(_env_file=None)

    assert settings.upload_max_bytes == 5242880
