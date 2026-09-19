"""Línea de tiempo de releases para la pantalla Versions (sección 7.4).

Función pura: recibe los tags ya leídos de git y tres funciones que saben
ir a buscar cosas (el dataset de una versión, su hash, el estado de un
remote). Leer git/DVC de verdad es trabajo de `pipeline/scripts/build_versions.py`;
así la lógica (qué se compara con qué, cómo se resumen los diffs, qué pasa
cuando un remote no responde) se prueba sin git, sin DVC y sin red.

El diff entre dos versiones lo calcula `compare_datasets` (el mismo que usa
`diff_release.py`); aquí solo se resume a conteos para la UI.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

from dataset_pipeline.analyzers import analyze_small_objects
from dataset_pipeline.coco.diff import compare_datasets
from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import images_per_category

RemoteStatus = Literal["in_sync", "missing", "unknown"]

_SEMVER = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class ReleaseTag:
    version: str
    message: str
    created_at: str
    commit: str


def semver_key(version: str) -> tuple[int, int, int]:
    match = _SEMVER.match(version)
    if match is None:
        raise ValueError(f"'{version}' no es una versión semántica (vMAJOR.MINOR.PATCH)")
    return int(match[1]), int(match[2]), int(match[3])


def snapshot(
    dataset: CocoDataset, min_images_per_class: int, small_object_threshold_px: int = 32
) -> dict:
    """Foto de una versión: con dos fotos la UI compara CUALESQUIERA dos
    releases (no solo vecinos) restando conteos, sin volver a leer datasets."""
    counts = images_per_category(dataset)
    return {
        "images": len(dataset.images),
        "boxes": len(dataset.annotations),
        "images_per_class": counts,
        "classes_below_minimum": sorted(
            name for name, count in counts.items() if count < min_images_per_class
        ),
        "small_objects_pct": analyze_small_objects(
            dataset, small_object_threshold_px
        ).percentage_below_threshold,
    }


def build_versions(
    tags: list[ReleaseTag],
    load_dataset: Callable[[str], CocoDataset | None],
    dataset_md5: Callable[[str], str | None],
    remote_status: Callable[[str, str], RemoteStatus],
    min_images_per_class: Callable[[str], int],
) -> dict:
    """Ordena los tags por semver (no alfabéticamente: v0.10.0 va después de
    v0.9.0) y arma un release por tag con su diff contra el anterior.

    `load_dataset` devuelve None cuando el dataset de esa versión no se pudo
    leer (sin credenciales, remote caído): el release aparece igual, con
    `diff_vs_previous: null` — la UI muestra "sin datos", no un diff inventado.
    """
    releases = []
    previous_version: str | None = None
    previous_dataset: CocoDataset | None = None

    for tag in sorted(tags, key=lambda t: semver_key(t.version)):
        dataset = load_dataset(tag.version)

        diff = None
        if dataset is not None and previous_dataset is not None and previous_version is not None:
            raw = compare_datasets(previous_dataset, dataset, min_images_per_class(tag.version))
            diff = {
                "from": previous_version,
                "to": tag.version,
                "images_added": len(raw["images_added"]),
                "images_removed": len(raw["images_removed"]),
                "boxes_added": len(raw["boxes_added"]),
                "boxes_removed": len(raw["boxes_removed"]),
                "images_per_class": raw["images_per_class"],
                "classes_below_minimum": raw["classes_below_minimum"],
                "classes_left_minimum": raw["classes_left_minimum"],
                "small_objects_pct_before": raw["small_objects_pct_before"],
                "small_objects_pct_after": raw["small_objects_pct_after"],
            }

        releases.append(
            {
                "version": tag.version,
                "message": tag.message,
                "created_at": tag.created_at,
                "commit": tag.commit,
                "dataset_md5": dataset_md5(tag.version),
                "snapshot": (
                    snapshot(dataset, min_images_per_class(tag.version))
                    if dataset is not None
                    else None
                ),
                "remotes": {
                    "dev": remote_status(tag.version, "dev"),
                    "prod": remote_status(tag.version, "prod"),
                },
                "diff_vs_previous": diff,
            }
        )

        if dataset is not None:
            previous_version, previous_dataset = tag.version, dataset

    return {"current": releases[-1]["version"] if releases else None, "releases": releases}
