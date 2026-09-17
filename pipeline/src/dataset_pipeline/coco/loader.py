import json
from pathlib import Path

from dataset_pipeline.coco.models import CocoDataset


def load_coco_dataset(path: str | Path) -> CocoDataset:
    """Lee y valida un export COCO del portal. Lanza `pydantic.ValidationError`
    con el campo exacto si el JSON no cumple el esquema."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return CocoDataset.model_validate(raw)
