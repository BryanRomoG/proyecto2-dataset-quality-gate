"""Etapa DVC "validate": carga y valida el COCO crudo (Frente 2), y lo
vuelve a serializar ya normalizado — cualquier COCO malformado truena aquí,
antes de que las etapas de análisis o split lo vean.
"""

import argparse
import json
from pathlib import Path

from dataset_pipeline.coco.loader import load_coco_dataset

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    dataset = load_coco_dataset(args.coco)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(dataset.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
