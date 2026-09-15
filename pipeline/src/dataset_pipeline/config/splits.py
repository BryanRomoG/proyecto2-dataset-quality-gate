"""Esquema de la configuración de splits (parámetros de entrada del Frente 5).

Valida forma y consistencia (seed presente, proporciones que suman 1.0);
la estratificación y el cero-fuga por pHash son responsabilidad del Frente 5.
"""

import math
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

SplitName = Literal["train", "val", "test"]


class SplitsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    ratios: dict[SplitName, float]

    @model_validator(mode="after")
    def ratios_sum_to_one(self) -> "SplitsConfig":
        missing = {"train", "val", "test"} - self.ratios.keys()
        if missing:
            raise ValueError(f"ratios: faltan las proporciones {sorted(missing)}")

        total = sum(self.ratios.values())
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"ratios: deben sumar 1.0, suman {total}")

        return self


def load_splits_config(path: str | Path) -> SplitsConfig:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return SplitsConfig.model_validate(raw)
