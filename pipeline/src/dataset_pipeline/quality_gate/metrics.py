"""Cálculo de métricas de calidad sobre un `CocoDataset` ya validado.

Cada función aquí es puro cómputo (sin I/O, sin conocer `quality.yaml`): la
comparación contra un umbral vive en `evaluator.py`. Así una métrica se
puede probar con datos en memoria, sin archivos ni configuración de por
medio.

El conteo de imágenes por clase (`images_per_category`) vive en
`dataset_pipeline.coco.stats` — Ale ya lo implementó para T-2.2 (class
imbalance) con la misma regla de M3 (imágenes DISTINTAS, no cajas). Este
módulo lo reusa en vez de mantener una segunda copia.
"""

from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import images_per_category


def min_images_per_class(dataset: CocoDataset) -> float:
    """El valor que decide M3: la clase con MENOS imágenes anotadas.

    min(...) >= 300 es equivalente a "todas las clases tienen >= 300", pero
    reduce el chequeo a un solo número comparable contra un único umbral en
    quality.yaml.
    """
    counts = images_per_category(dataset)
    if not counts:
        return 0.0
    return float(min(counts.values()))
