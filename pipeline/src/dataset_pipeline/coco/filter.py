"""Descartar categorías de un dataset COCO ya validado.

Caso de uso (T-2.2b): el equipo eligió dos clases (`car` y `person`), pero un
lote trae unas pocas cajas de una tercera (`bicycle`). `min_images_per_class`
toma el mínimo sobre TODAS las clases con datos, así que una clase con 11
imágenes deja la compuerta en 11 aunque las dos clases elegidas pasen de 300.

Función pura, igual que `merge_datasets`: solo transforma el `CocoDataset`
que recibe (no abre archivos ni toca imágenes).
"""

from collections.abc import Iterable

from dataset_pipeline.coco.models import CocoDataset


class UnknownCategoryError(ValueError):
    """Se pidió descartar una categoría que el dataset no tiene."""


def drop_categories(dataset: CocoDataset, names: Iterable[str]) -> CocoDataset:
    """Devuelve un dataset sin las categorías `names` ni sus anotaciones.

    - Las imágenes se conservan todas, aunque se queden sin ninguna caja: quitar
      imágenes es una decisión distinta (cambia el volumen) y no de este paso.
    - No se renumera ningún id: lo que queda conserva el id que tenía, así se
      sigue pudiendo rastrear contra el portal y contra los splits.
    - Un nombre que no existe falla con `UnknownCategoryError` en vez de no
      hacer nada en silencio (un typo dejaría la categoría adentro sin avisar).
    """
    to_drop = set(names)
    existing = {category.name for category in dataset.categories}

    unknown = sorted(to_drop - existing)
    if unknown:
        raise UnknownCategoryError(
            f"el dataset no tiene la(s) categoría(s) {unknown}; existentes: {sorted(existing)}"
        )

    dropped_ids = {category.id for category in dataset.categories if category.name in to_drop}

    return CocoDataset(
        info=dataset.info,
        licenses=dataset.licenses,
        images=list(dataset.images),
        annotations=[
            annotation
            for annotation in dataset.annotations
            if annotation.category_id not in dropped_ids
        ],
        categories=[category for category in dataset.categories if category.id not in dropped_ids],
    )
