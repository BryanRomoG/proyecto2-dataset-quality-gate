"""Frente 4 — cálculo de métricas sobre un CocoDataset ya validado (Frente 2).

`min_images_per_class` es el número que la compuerta compara contra M3 (300
imágenes por clase). El conteo "imágenes distintas, no cajas" en sí ya está
probado en pipeline/tests/coco/test_stats.py (Ale, T-2.2) — aquí solo se
prueba que min_images_per_class tome el mínimo correcto sobre ese conteo.
"""

from dataset_pipeline.coco.models import (
    CocoAnnotation,
    CocoCategory,
    CocoDataset,
    CocoImage,
    CocoInfo,
)
from dataset_pipeline.quality_gate.metrics import min_images_per_class

INFO = CocoInfo(description="test", version="1.0", date_created="2026-09-15T00:00:00.000Z")


def _image(image_id: int) -> CocoImage:
    return CocoImage(id=image_id, file_name=f"img-{image_id}.jpg", width=640, height=480)


def _annotation(ann_id: int, image_id: int, category_id: int) -> CocoAnnotation:
    return CocoAnnotation(
        id=ann_id,
        image_id=image_id,
        category_id=category_id,
        bbox=(0, 0, 10, 10),
        area=100,
        iscrowd=0,
        segmentation=[],
    )


def test_min_images_per_class_es_la_clase_con_menos_imagenes():
    dataset = CocoDataset(
        info=INFO,
        licenses=[],
        images=[_image(1), _image(2), _image(3)],
        annotations=[
            _annotation(1, image_id=1, category_id=1),
            _annotation(2, image_id=2, category_id=1),
            _annotation(3, image_id=3, category_id=1),
            _annotation(4, image_id=1, category_id=2),
        ],
        categories=[
            CocoCategory(id=1, name="car", supercategory="none"),
            CocoCategory(id=2, name="person", supercategory="none"),
        ],
    )

    # car=3 imágenes, person=1 imagen -> el mínimo (el que decide M3) es 1.
    assert min_images_per_class(dataset) == 1.0


def test_min_images_per_class_sin_categorias_es_cero():
    dataset = CocoDataset(info=INFO, licenses=[], images=[], annotations=[], categories=[])

    assert min_images_per_class(dataset) == 0.0
