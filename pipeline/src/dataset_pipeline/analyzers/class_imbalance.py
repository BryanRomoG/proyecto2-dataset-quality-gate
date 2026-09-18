"""SPEC-F3-02 — Desbalance de clases.

Recibe conteos ya calculados (p. ej. de `dataset_pipeline.coco.stats.
images_per_category`), no el dataset completo — así también sirve para los
checkpoints diarios de anotación (sección 3 del plan), que cuentan sobre la
base del portal en vivo, no sobre un COCO exportado.
"""

from pydantic import BaseModel, ConfigDict


class ClassImbalanceReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    counts: dict[str, int]
    majority_minority_ratio: float
    classes_below_minimum: list[str]


def analyze_class_imbalance(
    image_counts_per_class: dict[str, int],
    min_images_per_class: int,
) -> ClassImbalanceReport:
    if not image_counts_per_class:
        return ClassImbalanceReport(
            counts={},
            majority_minority_ratio=0.0,
            classes_below_minimum=[],
        )

    counts = list(image_counts_per_class.values())
    majority = max(counts)
    minority = min(counts)
    ratio = (majority / minority) if minority > 0 else float("inf")

    below_minimum = sorted(
        name for name, count in image_counts_per_class.items() if count < min_images_per_class
    )

    return ClassImbalanceReport(
        counts=dict(image_counts_per_class),
        majority_minority_ratio=ratio,
        classes_below_minimum=below_minimum,
    )
