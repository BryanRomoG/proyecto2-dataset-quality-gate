"""Diff de dataset entre dos versiones (tags/commits), vía la API de DVC —
no necesita checkout ni descargar todo el remote de nuevo, lee cada
revisión directamente del cache/remote configurado.

Reporta: imágenes agregadas/quitadas, cajas agregadas/quitadas, y qué
clases siguen (o empiezan a estar) por debajo del mínimo de quality.yaml.
"""

import argparse
import json
import subprocess

import dvc.api
import yaml

from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import images_per_category


def _load_dataset_at(rev: str) -> CocoDataset:
    raw = dvc.api.read("data/processed/coco.validated.json", rev=rev, mode="r")
    return CocoDataset.model_validate(json.loads(raw))


def _load_quality_policy_at(rev: str) -> dict:
    raw = subprocess.run(
        ["git", "show", f"{rev}:quality.yaml"], capture_output=True, text=True, check=True
    ).stdout
    return yaml.safe_load(raw)


def diff(rev_a: str, rev_b: str) -> dict:
    dataset_a = _load_dataset_at(rev_a)
    dataset_b = _load_dataset_at(rev_b)

    image_ids_a = {image.id for image in dataset_a.images}
    image_ids_b = {image.id for image in dataset_b.images}
    ann_ids_a = {ann.id for ann in dataset_a.annotations}
    ann_ids_b = {ann.id for ann in dataset_b.annotations}

    policy = _load_quality_policy_at(rev_b)
    min_threshold = policy["checks"]["min_images_per_class"]["threshold"]
    counts_b = images_per_category(dataset_b)
    below_minimum = sorted(name for name, count in counts_b.items() if count < min_threshold)

    return {
        "from": rev_a,
        "to": rev_b,
        "images_added": sorted(image_ids_b - image_ids_a),
        "images_removed": sorted(image_ids_a - image_ids_b),
        "boxes_added": sorted(ann_ids_b - ann_ids_a),
        "boxes_removed": sorted(ann_ids_a - ann_ids_b),
        "images_per_class": counts_b,
        "classes_below_minimum": below_minimum,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rev_a")
    parser.add_argument("rev_b")
    args = parser.parse_args()

    print(json.dumps(diff(args.rev_a, args.rev_b), indent=2))
