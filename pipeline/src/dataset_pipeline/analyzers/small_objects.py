"""SPEC-F3-01 — Detección de objetos pequeños.

Función pura: recibe el dataset y el umbral como parámetros, nunca lee
`quality.yaml` ni el entorno por su cuenta (eso le toca a quien la invoque,
la futura compuerta del Frente 4).
"""

from pydantic import BaseModel, ConfigDict

from dataset_pipeline.coco.models import CocoDataset


class SmallObjectsReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    threshold_px: int
    total_annotations: int
    small_count: int
    percentage_below_threshold: float
    most_affected_category: str | None
    offending_sample_ids: list[int]


def analyze_small_objects(
    dataset: CocoDataset,
    threshold_px: int,
    max_samples: int = 20,
) -> SmallObjectsReport:
    """Un objeto es "pequeño" si su área (width*height del bbox) es menor a
    `threshold_px ** 2` — la convención estándar de COCO para 32x32."""
    category_names = {category.id: category.name for category in dataset.categories}
    area_limit = threshold_px**2

    small_ids: list[int] = []
    small_count_by_category: dict[str, int] = {}
    total_count_by_category: dict[str, int] = {}

    for annotation in dataset.annotations:
        _, _, width, height = annotation.bbox
        area = abs(width) * abs(height)
        category_name = category_names.get(annotation.category_id, "unknown")
        total_count_by_category[category_name] = total_count_by_category.get(category_name, 0) + 1

        if area < area_limit:
            small_ids.append(annotation.id)
            small_count_by_category[category_name] = (
                small_count_by_category.get(category_name, 0) + 1
            )

    total = len(dataset.annotations)
    percentage = (len(small_ids) / total * 100) if total else 0.0

    most_affected = None
    if small_count_by_category:
        most_affected = max(
            small_count_by_category,
            key=lambda name: small_count_by_category[name] / total_count_by_category[name],
        )

    return SmallObjectsReport(
        threshold_px=threshold_px,
        total_annotations=total,
        small_count=len(small_ids),
        percentage_below_threshold=percentage,
        most_affected_category=most_affected,
        offending_sample_ids=small_ids[:max_samples],
    )
