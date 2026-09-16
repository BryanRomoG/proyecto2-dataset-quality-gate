"""Cálculo de métricas de calidad sobre un `CocoDataset` ya validado.

Cada función aquí es puro cómputo (sin I/O, sin conocer `quality.yaml`): la
comparación contra un umbral vive en `evaluator.py`. Así una métrica se
puede probar con datos en memoria, sin archivos ni configuración de por
medio.
"""

from collections import defaultdict

from dataset_pipeline.coco.models import CocoDataset


def images_per_class(dataset: CocoDataset) -> dict[str, int]:
    """Imágenes *distintas* con al menos una anotación por categoría.

    Una imagen con varias cajas de la misma clase cuenta una sola vez —
    es la misma regla que usa el evaluador humano para M3 (ver el plan de
    trabajo: "una foto con siete coches aporta una imagen a car, no siete").
    """
    category_names = {category.id: category.name for category in dataset.categories}
    images_by_category: dict[str, set[int]] = defaultdict(set)

    for annotation in dataset.annotations:
        name = category_names.get(annotation.category_id)
        if name is None:
            continue
        images_by_category[name].add(annotation.image_id)

    return {name: len(images_by_category[name]) for name in category_names.values()}


def min_images_per_class(dataset: CocoDataset) -> float:
    """El valor que decide M3: la clase con MENOS imágenes anotadas.

    min(...) >= 300 es equivalente a "todas las clases tienen >= 300", pero
    reduce el chequeo a un solo número comparable contra un único umbral en
    quality.yaml.
    """
    counts = images_per_class(dataset)
    if not counts:
        return 0.0
    return float(min(counts.values()))
