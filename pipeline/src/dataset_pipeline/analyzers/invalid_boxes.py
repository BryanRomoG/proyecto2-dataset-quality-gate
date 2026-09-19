"""SPEC-F3-04 — Cajas inválidas o degeneradas.

Detecta lo que la ingesta (T-1.3) deliberadamente deja pasar: width/height
negativos, cajas fuera de los límites de la imagen, y `area` incoherente
con width*height.
"""

from pydantic import BaseModel, ConfigDict

from dataset_pipeline.coco.models import CocoDataset


class InvalidBox(BaseModel):
    model_config = ConfigDict(extra="forbid")

    annotation_id: int
    reasons: list[str]


class InvalidBoxesReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_annotations: int
    invalid: list[InvalidBox]


def analyze_invalid_boxes(dataset: CocoDataset, area_tolerance: float = 1.0) -> InvalidBoxesReport:
    images_by_id = {image.id: image for image in dataset.images}

    invalid: list[InvalidBox] = []
    for annotation in dataset.annotations:
        reasons: list[str] = []
        x, y, width, height = annotation.bbox

        # width/height <= 0 es una caja degenerada: negativa o de área cero.
        # Se distinguen las dos para que el reporte diga qué pasó.
        if width < 0:
            reasons.append("negative_width")
        elif width == 0:
            reasons.append("zero_width")
        if height < 0:
            reasons.append("negative_height")
        elif height == 0:
            reasons.append("zero_height")

        image = images_by_id.get(annotation.image_id)
        if image is not None and (
            x < 0 or y < 0 or x + width > image.width or y + height > image.height
        ):
            reasons.append("out_of_image_bounds")

        expected_area = width * height
        if abs(annotation.area - expected_area) > area_tolerance:
            reasons.append("area_inconsistent_with_width_height")

        if reasons:
            invalid.append(InvalidBox(annotation_id=annotation.id, reasons=reasons))

    return InvalidBoxesReport(total_annotations=len(dataset.annotations), invalid=invalid)
