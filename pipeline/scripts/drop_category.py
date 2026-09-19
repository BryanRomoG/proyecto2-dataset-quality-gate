"""Quita una o más categorías (y sus cajas) de un COCO, sin tocar imágenes.

    python pipeline/scripts/drop_category.py \\
        --coco data/raw/coco.json --drop bicycle --out data/raw/coco.json

Solo transforma JSON, igual que `merge.py` y `validate.py`: no borra fotos.
Imprime cuántas imágenes se quedan sin ninguna caja, porque esas ya no cuentan
para ninguna clase y quizá convenga revisarlas.
"""

import argparse
import json
from pathlib import Path

from dataset_pipeline.coco.filter import drop_categories
from dataset_pipeline.coco.loader import load_coco_dataset
from dataset_pipeline.coco.stats import images_per_category

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco", required=True)
    parser.add_argument(
        "--drop",
        required=True,
        action="append",
        help="Nombre de la categoría a quitar. Repetible: --drop bicycle --drop dog",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    dataset = load_coco_dataset(args.coco)
    result = drop_categories(dataset, args.drop)

    annotated_image_ids = {annotation.image_id for annotation in result.annotations}
    without_boxes = [
        image.file_name for image in result.images if image.id not in annotated_image_ids
    ]

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )

    removed_boxes = len(dataset.annotations) - len(result.annotations)
    print(f"categorías quitadas: {args.drop} | cajas eliminadas: {removed_boxes}")
    print(f"imágenes por clase ahora: {images_per_category(result)}")
    print(f"imágenes que se quedaron sin ninguna caja: {len(without_boxes)}")
    for name in without_boxes:
        print(f"  - {name}")
