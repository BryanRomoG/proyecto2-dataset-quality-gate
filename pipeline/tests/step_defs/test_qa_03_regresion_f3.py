"""Step definitions de features/specs/qa-03-regresion-f3.feature.

SPEC-QA-03 (issue #16, T-3.5): corre el pipeline real (`dvc repro`) de
punta a punta contra el dataset real ya versionado (T-201..T-201c: 369
imágenes, car/person, compuerta en verde) y confirma que la compuerta de
Fase 2 sigue bloqueando de verdad con Fase 3 (splits) encima -- no un
COCO sintético de una sola etapa como en SPEC-F4-01.

Se salta si no hay datos reales en disco (mismo patrón que
test_f6_01_dvc_pipeline.py y SPEC-QA-02): no hay forma honesta de correr
`dvc repro` de verdad sin ellos, y fingir con un dataset falso no
demostraría lo que pide el issue.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml
from pytest_bdd import given, scenarios, then, when

REPO_ROOT = Path(__file__).parents[3]
PIPELINE_DIR = REPO_ROOT / "pipeline"
scenarios(str(REPO_ROOT / "features" / "specs" / "qa-03-regresion-f3.feature"))


@pytest.fixture
def context() -> dict:
    return {}


def _dvc(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["dvc", *args], cwd=REPO_ROOT, capture_output=True, text=True)


def _raw_data_available() -> bool:
    return (REPO_ROOT / "data" / "raw" / "coco.json").exists()


@given(
    "el dataset ingresado, analizado, filtrado por la compuerta, particionado y versionado",
    target_fixture="context",
)
def real_dataset_ready() -> dict:
    if not _raw_data_available():
        pytest.skip("data/raw/coco.json no está en disco -- corre 'dvc pull -r prod' primero")
    return {}


@when("se corre el pipeline completo sin intervención manual", target_fixture="context")
def run_full_pipeline(context: dict) -> dict:
    # No escribe el log en el repo (ensuciaría el working tree en cada
    # corrida) -- el log completo para el DoD del issue se adjunta a mano,
    # una vez, como comentario del issue en GitHub.
    context["result"] = _dvc("repro", "--force")
    return context


@then("cada etapa produce el output esperado por la siguiente")
def each_stage_feeds_the_next(context: dict) -> None:
    result = context["result"]
    assert result.returncode == 0, result.stderr

    validated = json.loads((REPO_ROOT / "data" / "processed" / "coco.validated.json").read_text())
    metrics_path = REPO_ROOT / "data" / "processed" / "quality_metrics.json"
    splits = json.loads((REPO_ROOT / "data" / "processed" / "splits.json").read_text())

    assert metrics_path.exists() and metrics_path.stat().st_size > 0

    # split consume el output de validate: mismo universo de imágenes.
    validated_ids = {image["id"] for image in validated["images"]}
    split_ids = {int(image_id) for image_id in splits["assignments"]}
    assert split_ids == validated_ids, "splits.json no cubre exactamente las imágenes validadas"

    total_assigned = sum(splits["counts"].values())
    assert total_assigned == len(validated_ids)

    context["validated"] = validated


@then("un fail inyectado en un split sigue bloqueando la promoción a PROD")
def injected_fail_still_blocks(context: dict, tmp_path: Path) -> None:
    # Mismo dataset real ya validado (con splits encima) -- no uno nuevo --
    # pero con un umbral imposible, igual que la verificación manual de
    # Control 2 (SPEC-F4-01): si esto no bloquea, la compuerta no protege
    # nada de verdad.
    policy = {"checks": {"min_images_per_class": {"threshold": 99999, "severity": "fail"}}}
    policy_path = tmp_path / "quality.impossible.yaml"
    policy_path.write_text(yaml.safe_dump(policy), encoding="utf-8")
    coco_path = REPO_ROOT / "data" / "processed" / "coco.validated.json"
    output_path = tmp_path / "quality.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dataset_pipeline.quality_gate.cli",
            "--coco",
            str(coco_path),
            "--policy",
            str(policy_path),
            "--output",
            str(output_path),
        ],
        cwd=PIPELINE_DIR,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, "la compuerta no bloqueó con un umbral imposible"
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["passed"] is False
