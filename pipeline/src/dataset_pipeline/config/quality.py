"""Esquema de `quality.yaml` (la política de la compuerta de calidad, Frente 4).

Valida solo la *forma* del contrato (qué checks existen, con qué severidad):
la lógica de qué umbral usa cada analizador es responsabilidad del Frente 4,
no de este módulo.

Regla del ticket: nunca usar el `dict` crudo de `yaml.safe_load()` en el resto
del código — siempre pasa primero por `QualityPolicy.model_validate(...)`.
"""

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

Severity = Literal["warn", "fail"]


class QualityCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold: float
    severity: Severity


class QualityPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    checks: dict[str, QualityCheck]

    @model_validator(mode="after")
    def require_min_images_per_class(self) -> "QualityPolicy":
        if "min_images_per_class" not in self.checks:
            raise ValueError(
                "quality.yaml debe definir el check 'min_images_per_class' (compuerta M3)"
            )
        return self


def load_quality_policy(path: str | Path) -> QualityPolicy:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return QualityPolicy.model_validate(raw)
