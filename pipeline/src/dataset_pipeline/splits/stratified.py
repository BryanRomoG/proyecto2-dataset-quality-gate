"""SPEC-F5-01..04 — Splits estratificados, reproducibles y sin fuga.

Función pura: recibe el dataset, las proporciones y la semilla como
parámetros (nunca lee quality.yaml ni el entorno por su cuenta). Los pares
de near-duplicates de T-2.2 son opcionales — sin ellos, sencillamente no
hay nada que agrupar y el comportamiento es el de un split estratificado
normal.

Estrategia:
1. Los pares de pHash se resuelven con union-find en "clusters": todas las
   imágenes de un mismo cluster van SIEMPRE al mismo split (cero fuga).
2. Cada cluster se estratifica por su "firma" (el conjunto de categorías
   presentes en sus imágenes), para que cada combinación de clases quede
   repartida proporcionalmente entre train/val/test.
3. El orden de barajado depende solo de `seed` y de los datos de entrada
   (nunca de `set`/`dict` sin ordenar primero) — dos corridas con la misma
   semilla producen exactamente la misma asignación.
"""

import random

from pydantic import BaseModel, ConfigDict

from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import image_category_signatures

SplitName = str  # "train" | "val" | "test", validado por SplitsConfig aguas arriba


class SplitResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seed: int
    ratios: dict[str, float]
    assignments: dict[int, SplitName]
    counts: dict[str, int]


def _find(parent: dict[int, int], node: int) -> int:
    while parent[node] != node:
        parent[node] = parent[parent[node]]
        node = parent[node]
    return node


def _union(parent: dict[int, int], a: int, b: int) -> None:
    root_a, root_b = _find(parent, a), _find(parent, b)
    if root_a != root_b:
        parent[root_a] = root_b


def _clusters_from_duplicate_pairs(
    image_ids: list[int],
    duplicate_pairs: list[tuple[int, int]],
) -> dict[int, list[int]]:
    """Agrupa imágenes en clusters vía union-find sobre los pares de pHash.
    Una imagen sin pares queda en su propio cluster de tamaño 1."""
    parent = {image_id: image_id for image_id in image_ids}

    for a, b in duplicate_pairs:
        if a in parent and b in parent:
            _union(parent, a, b)

    clusters: dict[int, list[int]] = {}
    for image_id in image_ids:
        root = _find(parent, image_id)
        clusters.setdefault(root, []).append(image_id)

    return clusters


def generate_stratified_splits(
    dataset: CocoDataset,
    ratios: dict[str, float],
    seed: int,
    duplicate_pairs: list[tuple[int, int]] | None = None,
) -> SplitResult:
    missing = {"train", "val", "test"} - ratios.keys()
    if missing:
        raise ValueError(f"ratios: faltan las proporciones {sorted(missing)}")

    signatures = image_category_signatures(dataset)
    image_ids = sorted(signatures.keys())  # orden determinista, no el del dict/set

    clusters = _clusters_from_duplicate_pairs(image_ids, duplicate_pairs or [])

    # Firma de un cluster = unión de las categorías de todas sus imágenes.
    cluster_signature: dict[int, frozenset[str]] = {
        root: frozenset().union(*(signatures[image_id] for image_id in members))
        for root, members in clusters.items()
    }

    buckets: dict[frozenset[str], list[int]] = {}
    for root, signature in cluster_signature.items():
        buckets.setdefault(signature, []).append(root)

    rng = random.Random(seed)
    assignments: dict[int, str] = {}

    for signature in sorted(buckets, key=lambda sig: sorted(sig)):
        roots = sorted(buckets[signature])  # orden determinista antes de barajar
        rng.shuffle(roots)

        total = len(roots)
        n_train = round(total * ratios["train"])
        n_val = round(total * ratios["val"])
        n_train = min(n_train, total)
        n_val = min(n_val, total - n_train)

        split_by_position = (
            ["train"] * n_train + ["val"] * n_val + ["test"] * (total - n_train - n_val)
        )

        for root, split_name in zip(roots, split_by_position, strict=True):
            for image_id in clusters[root]:
                assignments[image_id] = split_name

    counts = {"train": 0, "val": 0, "test": 0}
    for split_name in assignments.values():
        counts[split_name] += 1

    return SplitResult(seed=seed, ratios=dict(ratios), assignments=assignments, counts=counts)
