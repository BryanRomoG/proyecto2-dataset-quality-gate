"""Estadísticas puras sobre un `CocoDataset` ya validado."""

from dataset_pipeline.coco.models import CocoDataset


def images_per_category(dataset: CocoDataset) -> dict[str, int]:
    """Imágenes *distintas* con al menos una caja de cada categoría.

    Misma regla de conteo que la compuerta M3: una imagen con 7 cajas de
    "car" cuenta como 1 para "car", no como 7.
    """
    category_names = {category.id: category.name for category in dataset.categories}
    images_by_category: dict[str, set[int]] = {name: set() for name in category_names.values()}

    for annotation in dataset.annotations:
        name = category_names.get(annotation.category_id)
        if name is not None:
            images_by_category[name].add(annotation.image_id)

    return {name: len(image_ids) for name, image_ids in images_by_category.items()}
