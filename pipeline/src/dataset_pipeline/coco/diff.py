"""Diferencias entre dos versiones de un dataset COCO ya validado.

Función pura, igual que `merge_datasets` y `drop_categories`: solo compara los
`CocoDataset` que recibe. Leer cada versión de DVC/git es trabajo de quien la
invoque (`pipeline/scripts/diff_release.py`).

Reporta lo que pide un release con versión semántica: imágenes y cajas
añadidas/quitadas, imágenes por clase, clases que quedaron por debajo del
mínimo, clases que SALIERON del mínimo entre una versión y otra, y el cambio
en el porcentaje de objetos pequeños.
"""

from dataset_pipeline.analyzers import analyze_small_objects
from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import images_per_category


def compare_datasets(
    before: CocoDataset,
    after: CocoDataset,
    min_images_per_class: int,
    small_object_threshold_px: int = 32,
) -> dict:
    image_ids_before = {image.id for image in before.images}
    image_ids_after = {image.id for image in after.images}
    box_ids_before = {annotation.id for annotation in before.annotations}
    box_ids_after = {annotation.id for annotation in after.annotations}

    counts_before = images_per_category(before)
    counts_after = images_per_category(after)

    below_after = {name for name, count in counts_after.items() if count < min_images_per_class}
    # "Salió del mínimo": cumplía en la versión anterior y ya no cumple. Una clase
    # que ya estaba por debajo antes no es una salida nueva, es un problema viejo.
    met_before = {name for name, count in counts_before.items() if count >= min_images_per_class}

    small_before = analyze_small_objects(before, small_object_threshold_px)
    small_after = analyze_small_objects(after, small_object_threshold_px)
    pct_before = small_before.percentage_below_threshold
    pct_after = small_after.percentage_below_threshold

    return {
        "images_added": sorted(image_ids_after - image_ids_before),
        "images_removed": sorted(image_ids_before - image_ids_after),
        "boxes_added": sorted(box_ids_after - box_ids_before),
        "boxes_removed": sorted(box_ids_before - box_ids_after),
        "images_per_class": counts_after,
        "classes_below_minimum": sorted(below_after),
        "classes_left_minimum": sorted(met_before & below_after),
        "small_objects_pct_before": pct_before,
        "small_objects_pct_after": pct_after,
        "small_objects_pct_change": pct_after - pct_before,
    }
