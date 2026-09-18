"""Etapa DVC "split": genera train/val/test estratificado, usando los
pares de pHash que ya calculó la etapa "analyze" para garantizar cero fuga.
"""

import argparse
import json
from pathlib import Path

from dataset_pipeline.coco.loader import load_coco_dataset
from dataset_pipeline.config.splits import load_splits_config
from dataset_pipeline.splits import generate_stratified_splits

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--coco", required=True)
    parser.add_argument("--splits-config", required=True)
    parser.add_argument("--quality-metrics", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    dataset = load_coco_dataset(args.coco)
    config = load_splits_config(args.splits_config)

    quality_metrics = json.loads(Path(args.quality_metrics).read_text(encoding="utf-8"))
    duplicate_pairs = [
        (pair["image_id_a"], pair["image_id_b"])
        for pair in quality_metrics["duplicates"]["pairs"]
    ]

    result = generate_stratified_splits(
        dataset, config.ratios, config.seed, duplicate_pairs=duplicate_pairs
    )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(result.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
