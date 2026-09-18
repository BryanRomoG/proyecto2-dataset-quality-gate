"""Modelos de los contratos congelados que el Copilot puede leer (T-1.1,
issue #14): `quality.json`, `splits.json`, `versions.json`.

Igual que en `config/quality.py`: nunca se usa el `dict` crudo de
`json.loads()` en el resto del código del Copilot, siempre pasa primero por
uno de estos modelos. Así, si Frente 4/Frente 5 cambian la forma real del
archivo, una herramienta del Copilot truena con un error de validación claro
en vez de devolver `None`s silenciosos al modelo de lenguaje.
"""

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class QualityCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    value: float
    threshold: float
    direction: Literal["gte", "lte"]
    severity: Literal["warn", "fail"]
    passed: bool
    offending_samples: list[str]


class QualityReportContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    passed: bool
    checks: list[QualityCheckResult]


class SplitRatios(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train: float
    val: float
    test: float


class SplitCounts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    train: int
    val: int
    test: int


class SplitsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    ratios: SplitRatios
    assignments: dict[str, str]
    counts: SplitCounts


class VersionDiff(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    from_version: str = Field(alias="from")
    to_version: str = Field(alias="to")
    images_added: list[int]
    images_removed: list[int]
    boxes_added: list[int]
    boxes_removed: list[int]
    images_per_class: dict[str, int]
    classes_below_minimum: list[str]


class VersionRelease(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    message: str
    created_at: datetime
    dvc_rev: str
    diff_vs_previous: VersionDiff | None


class VersionsContract(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current: str
    releases: list[VersionRelease]


def load_quality(path: Path) -> QualityReportContract:
    return QualityReportContract.model_validate_json(path.read_text(encoding="utf-8"))


def load_splits(path: Path) -> SplitsContract:
    return SplitsContract.model_validate_json(path.read_text(encoding="utf-8"))


def load_versions(path: Path) -> VersionsContract:
    return VersionsContract.model_validate_json(path.read_text(encoding="utf-8"))
