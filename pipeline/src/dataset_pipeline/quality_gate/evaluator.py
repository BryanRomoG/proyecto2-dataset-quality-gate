"""Compara métricas ya calculadas contra la política de `quality.yaml`.

Este módulo no sabe nada de COCO ni de archivos: recibe un dict de valores
ya calculados (`{"min_images_per_class": 287.0, ...}`) y una `QualityPolicy`
ya validada (Frente 2), y decide pass/fail por check y en conjunto.

La dirección de la comparación (¿más alto es mejor, o más bajo?) es una
decisión de negocio por métrica, y vive aquí — es justo la responsabilidad
que el docstring de `config/quality.py` deja explícitamente para el Frente 4.
"""

from dataclasses import dataclass
from typing import Literal

from dataset_pipeline.config import QualityPolicy

Direction = Literal["gte", "lte"]

# Una métrica nueva (de un analizador del Frente 3) se agrega aquí con su
# dirección: "gte" si más alto es mejor (ej. imágenes por clase), "lte" si
# más bajo es mejor (ej. proporción de objetos pequeños, de duplicados).
_CHECK_DIRECTIONS: dict[str, Direction] = {
    "min_images_per_class": "gte",
    "invalid_boxes_count": "lte",
}


class UnknownCheckError(Exception):
    """quality.yaml declara un check para el que no hay valor calculado.

    Pasa cuando el check no está en `metric_values` (nadie llamó a su
    analizador todavía) o cuando no tiene una dirección de comparación
    registrada en `_CHECK_DIRECTIONS` (nadie decidió todavía si más alto o
    más bajo es mejor). En ambos casos la compuerta se niega a evaluarlo en
    silencio: o se implementa la métrica, o se quita el check de
    quality.yaml — nunca se ignora sin decirlo.
    """


@dataclass(frozen=True)
class CheckResult:
    name: str
    value: float
    threshold: float
    direction: Direction
    severity: Literal["warn", "fail"]
    passed: bool
    # SPEC-F4-04: el reporte no es solo un booleano — trae valor vs umbral
    # (arriba) y, cuando el analizador correspondiente las provee, las
    # muestras concretas que ofenden el check (nombres de clase, IDs de
    # anotación, etc.). Lista vacía si nadie las proveyó, nunca None.
    offending_samples: list[str]


@dataclass(frozen=True)
class QualityReport:
    checks: list[CheckResult]
    passed: bool


def _compare(value: float, threshold: float, direction: Direction) -> bool:
    if direction == "gte":
        return value >= threshold
    return value <= threshold


def evaluate(
    metric_values: dict[str, float],
    policy: QualityPolicy,
    offending_samples: dict[str, list[str]] | None = None,
) -> QualityReport:
    offending_samples = offending_samples or {}
    results: list[CheckResult] = []

    for name, check in policy.checks.items():
        if name not in metric_values:
            raise UnknownCheckError(
                f"quality.yaml define el check '{name}' pero no se calculó ningún valor "
                "para él (¿falta implementar o registrar su analizador?)"
            )
        direction = _CHECK_DIRECTIONS.get(name)
        if direction is None:
            raise UnknownCheckError(
                f"el check '{name}' no tiene una dirección de comparación registrada "
                "en quality_gate/evaluator.py (_CHECK_DIRECTIONS)"
            )

        value = metric_values[name]
        passed = _compare(value, check.threshold, direction)
        results.append(
            CheckResult(
                name=name,
                value=value,
                threshold=check.threshold,
                direction=direction,
                severity=check.severity,
                passed=passed,
                offending_samples=offending_samples.get(name, []),
            )
        )

    overall_passed = all(result.passed for result in results if result.severity == "fail")
    return QualityReport(checks=results, passed=overall_passed)
