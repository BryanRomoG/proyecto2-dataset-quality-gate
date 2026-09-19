"""Genera `data/processed/versions.json`: la línea de tiempo de releases que
muestra la pantalla Versions (versión, diff contra la anterior y estado
DEV / PROD de cada una).

    python pipeline/scripts/build_versions.py --out data/processed/versions.json

Lee los tags semver de git, el hash del dataset de cada tag desde su
`dvc.lock`, y el dataset de cada versión con la API de DVC (igual que
`diff_release.py`). Necesita acceso a los remotes: lo que no se pueda leer
(sin credenciales, remote caído) queda como `unknown` / sin diff, nunca como
un dato inventado.
"""

import argparse
import json
import re
import subprocess
from pathlib import Path

import dvc.api
import yaml

from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.releases import ReleaseTag, RemoteStatus, build_versions
from dataset_pipeline.config.quality import parse_quality_policy

DATASET_PATH = "data/processed/coco.validated.json"
SEMVER_TAG = re.compile(r"^v\d+\.\d+\.\d+$")
# Mensajes con los que S3/MinIO/DVC dicen "el objeto no está" (≠ "no pude preguntar").
MISSING_MARKERS = ("nosuchkey", "not found", "404", "does not exist", "no such file")


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], capture_output=True, text=True, check=True).stdout


def _read_tags() -> list[ReleaseTag]:
    fmt = "%(refname:short)|%(creatordate:iso-strict)|%(subject)|%(objectname:short)"
    tags = []
    for line in _git("tag", "-l", "--format", fmt).splitlines():
        version, created_at, message, commit = line.split("|", 3)
        if SEMVER_TAG.match(version):
            tags.append(ReleaseTag(version, message, created_at, commit))
    return tags


def _dataset_md5(version: str) -> str | None:
    try:
        lock = yaml.safe_load(_git("show", f"{version}:dvc.lock"))
        outs = lock["stages"]["validate"]["outs"]
        return next(out["md5"] for out in outs if out["path"] == DATASET_PATH)
    except (subprocess.CalledProcessError, KeyError, StopIteration, TypeError):
        return None


def _load_dataset(version: str, remote: str) -> CocoDataset | None:
    try:
        raw = dvc.api.read(DATASET_PATH, rev=version, remote=remote, mode="r")
    except Exception as error:  # sin credenciales / remote caído: el release sigue, sin diff
        print(f"aviso: no pude leer {version} de '{remote}': {error}")
        return None
    return CocoDataset.model_validate(json.loads(raw))


def _remote_status(version: str, remote: str) -> RemoteStatus:
    """`in_sync` = DVC pudo bajar del remote el objeto con el hash que el tag
    declara (el mismo md5 que en el otro remote). `missing` = el remote
    contestó que no lo tiene. `unknown` = no se pudo preguntar."""
    try:
        dvc.api.read(DATASET_PATH, rev=version, remote=remote, mode="r")
    except Exception as error:
        text = str(error).lower()
        return "missing" if any(marker in text for marker in MISSING_MARKERS) else "unknown"
    return "in_sync"


def _min_images_per_class(version: str) -> int:
    try:
        policy = parse_quality_policy(_git("show", f"{version}:quality.yaml"))
    except subprocess.CalledProcessError:
        policy = parse_quality_policy(Path("quality.yaml").read_text(encoding="utf-8"))
    return int(policy.checks["min_images_per_class"].threshold)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument(
        "--dataset-remote",
        default="prod",
        help="Remote del que se lee el dataset de cada versión (las viejas solo viven en PROD)",
    )
    args = parser.parse_args()

    result = build_versions(
        _read_tags(),
        load_dataset=lambda version: _load_dataset(version, args.dataset_remote),
        dataset_md5=_dataset_md5,
        remote_status=_remote_status,
        min_images_per_class=_min_images_per_class,
    )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"{len(result['releases'])} release(s) -> {args.out}")
