"""Genera un COCO de muestra (con imágenes reales, no solo metadata) para
poder correr y probar el pipeline DVC de punta a punta mientras T-101 (los
contratos congelados) y la integración real con el export del portal no
existan todavía.

No es el dataset real del curso — es un stand-in explícito, documentado en
pipeline/README.md, que se reemplaza por el export real de
server/src/export/coco.service.ts (imágenes vía MinIO) en cuanto esa pieza
esté conectada. Incluye a propósito una imagen duplicada (recomprimida, con
otro nombre) para que la etapa de análisis tenga algo real que detectar.
"""

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw


def _draw_image(path: Path, seed: int) -> None:
    img = Image.new("RGB", (200, 200), color=(230, 230, 230))
    draw = ImageDraw.Draw(img)
    x = 10 + (seed * 17) % 100
    y = 10 + (seed * 31) % 100
    draw.rectangle([x, y, x + 60, y + 60], fill=((seed * 53) % 255, 60, 160))
    draw.ellipse([20, 120, 120, 190], fill=(30, 160, (seed * 29) % 255))
    img.save(path, format="JPEG", quality=90)


def generate(images_per_class: int, images_dir: Path) -> dict:
    categories = [
        {"id": 1, "name": "car", "supercategory": "none"},
        {"id": 2, "name": "person", "supercategory": "none"},
    ]

    images = []
    annotations = []
    ann_id = 1

    for category in categories:
        for i in range(images_per_class):
            image_id = category["id"] * 100_000 + i
            file_name = f"{category['name']}-{i:04d}.jpg"
            _draw_image(images_dir / file_name, seed=image_id)

            images.append(
                {"id": image_id, "file_name": file_name, "width": 200, "height": 200}
            )
            annotations.append(
                {
                    "id": ann_id,
                    "image_id": image_id,
                    "category_id": category["id"],
                    "bbox": [10 + i % 50, 10 + i % 40, 80 + i % 100, 60 + i % 100],
                    "area": (80 + i % 100) * (60 + i % 100),
                    "iscrowd": 0,
                    "segmentation": [],
                }
            )
            ann_id += 1

    # Duplicado deliberado: misma imagen que car-0000.jpg, recomprimida y
    # con otro nombre — para que la etapa de análisis tenga un caso real
    # de near-duplicate que detectar (SPEC-F3-03).
    original_path = images_dir / "car-0000.jpg"
    duplicate_id = 999999
    duplicate_name = "car-0000-copia-recomprimida.jpg"
    Image.open(original_path).convert("RGB").save(
        images_dir / duplicate_name, format="JPEG", quality=35
    )
    images.append({"id": duplicate_id, "file_name": duplicate_name, "width": 200, "height": 200})
    annotations.append(
        {
            "id": ann_id,
            "image_id": duplicate_id,
            "category_id": 1,
            "bbox": [10, 10, 80, 60],
            "area": 4800,
            "iscrowd": 0,
            "segmentation": [],
        }
    )

    return {
        "info": {
            "description": "Dataset de muestra (generado) para probar el pipeline DVC",
            "version": "0.0.0-sample",
            "date_created": "2026-01-01T00:00:00.000Z",
        },
        "licenses": [],
        "images": images,
        "annotations": annotations,
        "categories": categories,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--images-per-class", type=int, default=15)
    parser.add_argument("--out", required=True, help="Ruta del coco.json de salida")
    parser.add_argument(
        "--images-dir", required=True, help="Carpeta donde se escriben los .jpg"
    )
    args = parser.parse_args()

    images_dir = Path(args.images_dir)
    images_dir.mkdir(parents=True, exist_ok=True)

    coco = generate(args.images_per_class, images_dir)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(coco, indent=2), encoding="utf-8")
