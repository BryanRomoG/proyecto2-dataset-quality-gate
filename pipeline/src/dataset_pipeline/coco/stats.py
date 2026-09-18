"""Estadísticas puras sobre un `CocoDataset` ya validado."""

from dataset_pipeline.coco.models import CocoDataset


def image_category_signatures(dataset: CocoDataset) -> dict[int, frozenset[str]]:
    """Para cada imagen, el conjunto de categorías de las que tiene al menos
    una caja. Una imagen sin ninguna anotación tiene firma vacía."""
    category_names = {category.id: category.name for category in dataset.categories}
    signatures: dict[int, set[str]] = {image.id: set() for image in dataset.images}

    for annotation in dataset.annotations:
        name = category_names.get(annotation.category_id)
        if name is not None and annotation.image_id in signatures:
            signatures[annotation.image_id].add(name)

    return {image_id: frozenset(names) for image_id, names in signatures.items()}


def images_per_category(dataset: CocoDataset) -> dict[str, int]:
    """Imágenes *distintas* con al menos una caja de cada categoría.

    Misma regla de conteo que la compuerta M3: una imagen con 7 cajas de
    "car" cuenta como 1 para "car", no como 7.
    """
    counts = {category.name: 0 for category in dataset.categories}

    for signature in image_category_signatures(dataset).values():
        for name in signature:
            counts[name] += 1

    return counts
