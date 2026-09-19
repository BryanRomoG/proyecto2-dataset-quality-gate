"""Diff de dataset entre dos versiones (tags/commits), vía la API de DVC —
no necesita checkout ni descargar todo el remote de nuevo, lee cada
revisión directamente de un remote.

Reporta: imágenes y cajas agregadas/quitadas, imágenes por clase, clases por
debajo del mínimo de quality.yaml, clases que SALIERON del mínimo entre las dos
versiones, y el cambio en el porcentaje de objetos pequeños. La comparación
vive en `dataset_pipeline.coco.diff` (función pura, con pruebas).

    python pipeline/scripts/diff_release.py v0.3.0 v1.0.0 --remote prod

`--remote prod` porque las versiones anteriores solo están en PROD; DEV (MinIO
local) guarda lo último que se empujó ahí.
"""

import argparse
import json
import subprocess

import dvc.api

from dataset_pipeline.coco.diff import compare_datasets
from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.config.quality import QualityPolicy, parse_quality_policy


def _load_dataset_at(rev: str, remote: str | None) -> CocoDataset:
    raw = dvc.api.read("data/processed/coco.validated.json", rev=rev, remote=remote, mode="r")
    return CocoDataset.model_validate(json.loads(raw))


def _load_quality_policy_at(rev: str) -> QualityPolicy:
    raw = subprocess.run(
        ["git", "show", f"{rev}:quality.yaml"], capture_output=True, text=True, check=True
    ).stdout
    return parse_quality_policy(raw)


def diff(rev_a: str, rev_b: str, remote: str | None = None) -> dict:
    dataset_a = _load_dataset_at(rev_a, remote)
    dataset_b = _load_dataset_at(rev_b, remote)
    policy = _load_quality_policy_at(rev_b)
    min_threshold = int(policy.checks["min_images_per_class"].threshold)

    return {"from": rev_a, "to": rev_b, **compare_datasets(dataset_a, dataset_b, min_threshold)}


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("rev_a")
    parser.add_argument("rev_b")
    parser.add_argument(
        "--remote",
        default=None,
        help="Remote DVC de donde leer cada versión (default: el remote por defecto de DVC)",
    )
    args = parser.parse_args()

    print(json.dumps(diff(args.rev_a, args.rev_b, args.remote), indent=2))
