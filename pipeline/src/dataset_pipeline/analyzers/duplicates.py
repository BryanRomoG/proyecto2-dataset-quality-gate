"""SPEC-F3-03 — Duplicados y near-duplicates por pHash.

Usa `imagehash` (perceptual hashing) en vez de compararlas por hash exacto
(MD5/SHA), que no detecta una copia recomprimida —el plan de trabajo pide
explícitamente usar una librería en vez de implementar el hashing perceptual
a mano.

Recibe las imágenes ya cargadas en memoria (`PIL.Image.Image`); esta función
no abre ningún archivo, bucket ni conexión por su cuenta.
"""

from itertools import combinations

import imagehash
from PIL import Image
from pydantic import BaseModel, ConfigDict


class DuplicatePair(BaseModel):
    model_config = ConfigDict(extra="forbid")

    image_id_a: int
    image_id_b: int
    hash_distance: int
    similarity: float


class DuplicatesReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distance_threshold: int
    pairs: list[DuplicatePair]


def find_duplicate_pairs(
    images: dict[int, Image.Image],
    distance_threshold: int,
) -> DuplicatesReport:
    hashes = {image_id: imagehash.phash(image) for image_id, image in images.items()}
    max_bits = hashes[next(iter(hashes))].hash.size if hashes else 64

    pairs: list[DuplicatePair] = []
    for (id_a, hash_a), (id_b, hash_b) in combinations(hashes.items(), 2):
        distance = hash_a - hash_b  # distancia de Hamming
        if distance <= distance_threshold:
            similarity = 1 - (distance / max_bits)
            pairs.append(
                DuplicatePair(
                    image_id_a=id_a,
                    image_id_b=id_b,
                    hash_distance=distance,
                    similarity=similarity,
                )
            )

    return DuplicatesReport(distance_threshold=distance_threshold, pairs=pairs)
