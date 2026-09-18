"""Etapa DVC "analyze": corre los 5 analizadores del Frente 3 sobre el COCO
ya validado y escribe un reporte combinado.

Los umbrales de cada analizador se reciben como argumentos de línea de
comandos (con default documentado aquí), nunca hardcodeados dentro de los
analizadores mismos — son estos, y no los analizadores, quienes conocen la
política del proyecto.
"""

import argparse
import json
from pathlib import Path

from PIL import Image

from dataset_pipeline.analyzers import (
    analyze_class_imbalance,
    analyze_invalid_boxes,
    analyze_small_objects,
    analyze_spatial_bias,
    find_duplicate_pairs,
)
from dataset_pipeline.coco.loader import load_coco_dataset
from dataset_pipeline.coco.stats import images_per_category
from dataset_pipeline.config.quality import load_quality_policy


def _load_images(dataset, images_dir: Path) -> dict[int, Image.Image]:
    images = {}
    for image in dataset.images:
        path = images_dir / image.file_name
        if path.exists():
            images[image.id] = Image.open(path).convert("RGB")
    return images


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--quality-policy", required=True, help="Ruta a quality.yaml")
    parser.add_argument("--out", required=True)
    # Umbrales *definicionales* de cada analizador (qué cuenta como "pequeño",
    # qué distancia de pHash cuenta como duplicado): no viven en quality.yaml
    # porque ese archivo declara la *política* (umbral aceptable + severidad),
    # no la definición de cada métrica. Configurables aquí, no hardcodeados
    # dentro de los analizadores.
    parser.add_argument("--small-objects-threshold-px", type=int, default=32)
    parser.add_argument("--duplicate-distance-threshold", type=int, default=8)
    args = parser.parse_args()

    dataset = load_coco_dataset(args.coco)
    images_dir = Path(args.images_dir)
    policy = load_quality_policy(args.quality_policy)
    min_images_per_class = int(policy.checks["min_images_per_class"].threshold)

    small_objects_report = analyze_small_objects(dataset, args.small_objects_threshold_px)
    class_imbalance_report = analyze_class_imbalance(
        images_per_category(dataset), min_images_per_class
    )
    invalid_boxes_report = analyze_invalid_boxes(dataset)

    areas = [bbox[2] * bbox[3] for bbox in (ann.bbox for ann in dataset.annotations)]
    spatial_bias_report = analyze_spatial_bias(areas)

    loaded_images = _load_images(dataset, images_dir)
    duplicates_report = find_duplicate_pairs(loaded_images, args.duplicate_distance_threshold)

    report = {
        "small_objects": small_objects_report.model_dump(mode="json"),
        "class_imbalance": class_imbalance_report.model_dump(mode="json"),
        "invalid_boxes": invalid_boxes_report.model_dump(mode="json"),
        "spatial_bias": spatial_bias_report.model_dump(mode="json"),
        "duplicates": duplicates_report.model_dump(mode="json"),
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
