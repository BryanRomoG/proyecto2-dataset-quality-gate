"""Etapa DVC "embed": proyección PCA 2D precomputada para la analítica
exploratoria de la app web (pestaña Explorar).

Se calcula aquí, una vez por corrida del pipeline; el navegador solo lee el
JSON y filtra/hoverea sin volver a llamar al servidor.
"""

import argparse
import json
from pathlib import Path

from PIL import Image

from dataset_pipeline.coco.embedding import build_embedding, image_features
from dataset_pipeline.coco.loader import load_coco_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco", required=True)
    parser.add_argument("--images-dir", required=True)
    parser.add_argument("--splits", help="splits.json (opcional): colorea la nube por split")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    dataset = load_coco_dataset(args.coco)
    images_dir = Path(args.images_dir)

    features = {}
    for image in dataset.images:
        path = images_dir / image.file_name
        if path.exists():
            with Image.open(path) as opened:
                features[image.id] = image_features(opened)

    split_by_image: dict[int, str] = {}
    if args.splits:
        assignments = json.loads(Path(args.splits).read_text(encoding="utf-8"))["assignments"]
        split_by_image = {int(image_id): split for image_id, split in assignments.items()}

    artifact = build_embedding(dataset, features, split_by_image)

    skipped = len(dataset.images) - len(features)
    if skipped:
        print(f"aviso: {skipped} imagen(es) sin archivo en {images_dir}; quedan fuera de la nube")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    # allow_nan=False: un NaN produciría un JSON que el server no puede leer.
    Path(args.out).write_text(json.dumps(artifact, allow_nan=False), encoding="utf-8")
