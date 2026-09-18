"""Fusión de un lote nuevo de anotaciones sobre un dataset COCO base.

Frente 6 (T-3.2b): cuando dos contribuidores anotan en su propio portal
local (su propia MariaDB/MinIO) y exportan cada uno un COCO, no hay forma de
que sus `image_id`/`annotation_id` no colisionen — cada export vuelve a
contar desde donde su propia base de datos empezó. Esta función resuelve la
fusión sin fuga de identidad: reasigna los ids del lote entrante a partir
del máximo ya usado en el dataset base, y unifica las categorías por
*nombre* (no por id numérico, porque dos exports pueden asignarle ids
distintos a la misma clase).

Función pura: solo transforma los `CocoDataset` que recibe, igual que los
analizadores de `dataset_pipeline.analyzers` — no abre archivos ni copia
imágenes. Copiar los `.jpg` del lote a `data/raw/images/` sigue siendo un
paso manual (ver `pipeline/scripts/merge.py` y `pipeline/README.md`).
"""

from dataset_pipeline.coco.models import CocoCategory, CocoDataset


class MergeError(ValueError):
    """Un lote no se puede fusionar tal cual está (p. ej. colisión de archivo)."""


def merge_datasets(base: CocoDataset, incoming: CocoDataset) -> CocoDataset:
    """Fusiona `incoming` sobre `base` sin colisión de ids.

    - Categorías: se unifican por `name`. Un nombre que ya existe en `base`
      reutiliza su id; uno nuevo recibe `max(ids existentes) + 1`.
    - `image.id` / `annotation.id` de `incoming`: se reasignan a partir del
      máximo id ya usado en `base`, recorriendo listas siempre **ordenadas**
      por id original (nunca la iteración de un dict/set) para que dos
      corridas con la misma entrada den siempre el mismo resultado.
    - `file_name`: si una imagen de `incoming` ya existe en `base` con ese
      mismo nombre, se rechaza con `MergeError` nombrando el archivo — no se
      renombra en silencio, porque dos imágenes distintas no pueden compartir
      nombre en `data/raw/images/` y solo un humano puede decidir cuál es la
      correcta.

    Los `image_id`/`category_id` de cada anotación de `incoming` están
    garantizados por `CocoDataset.check_references` (ver `coco/models.py`)
    a existir dentro de `incoming` — por eso los remaps se indexan
    directamente, sin `.get()` defensivo.
    """
    base_filenames = {image.file_name for image in base.images}
    colliding = sorted(
        image.file_name for image in incoming.images if image.file_name in base_filenames
    )
    if colliding:
        raise MergeError(
            "colisión de file_name entre el lote entrante y el dataset base "
            f"(ya existen): {colliding}"
        )

    categories = list(base.categories)
    category_by_name = {category.name: category.id for category in categories}
    next_category_id = max((category.id for category in categories), default=0) + 1
    category_id_remap: dict[int, int] = {}

    for category in sorted(incoming.categories, key=lambda c: c.id):
        existing_id = category_by_name.get(category.name)
        if existing_id is not None:
            category_id_remap[category.id] = existing_id
            continue
        categories.append(
            CocoCategory(
                id=next_category_id,
                name=category.name,
                supercategory=category.supercategory,
            )
        )
        category_by_name[category.name] = next_category_id
        category_id_remap[category.id] = next_category_id
        next_category_id += 1

    next_image_id = max((image.id for image in base.images), default=0) + 1
    image_id_remap: dict[int, int] = {}
    images = list(base.images)
    for image in sorted(incoming.images, key=lambda i: i.id):
        image_id_remap[image.id] = next_image_id
        images.append(image.model_copy(update={"id": next_image_id}))
        next_image_id += 1

    next_annotation_id = max((annotation.id for annotation in base.annotations), default=0) + 1
    annotations = list(base.annotations)
    for annotation in sorted(incoming.annotations, key=lambda a: a.id):
        annotations.append(
            annotation.model_copy(
                update={
                    "id": next_annotation_id,
                    "image_id": image_id_remap[annotation.image_id],
                    "category_id": category_id_remap[annotation.category_id],
                }
            )
        )
        next_annotation_id += 1

    return CocoDataset(
        info=base.info,
        licenses=base.licenses,
        images=images,
        annotations=annotations,
        categories=categories,
    )
