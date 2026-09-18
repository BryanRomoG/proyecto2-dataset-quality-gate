"""Fusiona uno o más lotes COCO de otros contribuidores sobre un dataset base,
sin colisión de `image_id`/`annotation_id` (Frente 6, T-3.2b).

Solo transforma JSON: copiar los `.jpg` del lote a `data/raw/images/` sigue
siendo un paso manual (ver `pipeline/README.md`), igual que `validate.py`
tampoco toca archivos de imagen.
"""

import argparse
import json
from functools import reduce
from pathlib import Path

from dataset_pipeline.coco.loader import load_coco_dataset
from dataset_pipeline.coco.merge import merge_datasets

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--base",
        required=False,
        help="COCO base ya compartido (p. ej. data/raw/coco.json). Si se omite, "
        "el primer --batch se usa como base (primer lote del dataset).",
    )
    parser.add_argument(
        "--batch",
        required=True,
        action="append",
        help="COCO de un lote a fusionar. Repetible: --batch a.json --batch b.json",
    )
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    batches = [load_coco_dataset(path) for path in args.batch]

    if args.base:
        seed = load_coco_dataset(args.base)
        to_merge = batches
    else:
        seed, *to_merge = batches

    merged = reduce(merge_datasets, to_merge, seed)

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(merged.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
