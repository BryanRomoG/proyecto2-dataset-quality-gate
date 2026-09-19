"""Proyección 2D del dataset para la analítica exploratoria (sección 7.6).

Se calcula OFFLINE (etapa `embed` del pipeline) y la app solo la lee: el
navegador nunca recalcula la reducción dimensional. Cada imagen se describe
con un vector de rasgos simples y reproducibles (miniatura RGB + histograma
de color) y se proyecta con PCA vía SVD de NumPy.

PCA y no t-SNE/UMAP a propósito: es determinista (mismo dato, misma
proyección, sin semilla que fijar), no añade dependencias pesadas y sus
componentes se pueden explicar (`explained_variance`). Los rasgos son de
píxeles, no de un modelo de visión: la nube agrupa imágenes por apariencia
global (brillo, color, composición), no por semántica.

Funciones puras sobre imágenes/arrays ya cargados: leer archivos y escribir
el JSON es trabajo de `pipeline/scripts/embed.py`.
"""

from __future__ import annotations

import numpy as np
from PIL import Image

from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import image_category_signatures

THUMBNAIL_SIDE = 8
HISTOGRAM_BINS = 16


def image_features(image: Image.Image) -> np.ndarray:
    """Vector de rasgos de una imagen: miniatura 8x8 RGB (192) + histograma de
    16 bins por canal (48), todo normalizado a [0, 1]."""
    rgb = image.convert("RGB")
    thumbnail = np.asarray(rgb.resize((THUMBNAIL_SIDE, THUMBNAIL_SIDE)), dtype=np.float64) / 255.0

    pixels = np.asarray(rgb, dtype=np.float64).reshape(-1, 3)
    histogram = np.concatenate(
        [
            np.histogram(pixels[:, channel], bins=HISTOGRAM_BINS, range=(0.0, 256.0))[0]
            for channel in range(3)
        ]
    ).astype(np.float64)
    histogram /= max(pixels.shape[0], 1)

    return np.concatenate([thumbnail.ravel(), histogram])


def project_pca(features: np.ndarray, n_components: int = 2) -> tuple[np.ndarray, list[float]]:
    """PCA por SVD. Devuelve (coordenadas [n, n_components], varianza explicada
    por componente).

    Con menos de 2 imágenes, o rasgos constantes, no hay varianza que
    proyectar: se devuelven ceros en vez de NaN, para que el JSON sea válido.
    """
    n_samples = features.shape[0]
    if n_samples == 0:
        return np.zeros((0, n_components)), [0.0] * n_components

    centered = features - features.mean(axis=0, keepdims=True)
    if n_samples < 2 or not np.any(centered):
        return np.zeros((n_samples, n_components)), [0.0] * n_components

    _, singular_values, components = np.linalg.svd(centered, full_matrices=False)

    # El signo de cada componente es arbitrario en SVD: se fija para que dos
    # corridas (o dos versiones de NumPy) den la misma nube, no una espejada.
    for index in range(components.shape[0]):
        pivot = np.argmax(np.abs(components[index]))
        if components[index, pivot] < 0:
            components[index] = -components[index]

    kept = min(n_components, components.shape[0])
    coordinates = np.zeros((n_samples, n_components))
    coordinates[:, :kept] = centered @ components[:kept].T

    variance = singular_values**2
    total = variance.sum()
    explained = [
        float(variance[i] / total) if i < kept and total > 0 else 0.0 for i in range(n_components)
    ]
    return coordinates, explained


def build_embedding(
    dataset: CocoDataset,
    features_by_image: dict[int, np.ndarray],
    split_by_image: dict[int, str] | None = None,
) -> dict:
    """Arma el artefacto `embedding.json`. Las imágenes sin rasgos (archivo no
    materializado) quedan fuera en vez de inventarles una posición."""
    split_by_image = split_by_image or {}
    signatures = image_category_signatures(dataset)
    images = sorted(
        (image for image in dataset.images if image.id in features_by_image),
        key=lambda image: image.id,
    )

    matrix = (
        np.stack([features_by_image[image.id] for image in images]) if images else np.zeros((0, 1))
    )
    coordinates, explained = project_pca(matrix)

    return {
        "method": "pca",
        "explained_variance": explained,
        "points": [
            {
                "image_id": image.id,
                "file_name": image.file_name,
                "x": float(coordinates[index, 0]),
                "y": float(coordinates[index, 1]),
                "categories": sorted(signatures.get(image.id, frozenset())),
                "split": split_by_image.get(image.id),
            }
            for index, image in enumerate(images)
        ],
    }
