"""Frente 4 — extremo a extremo, incluyendo el exit code real del proceso.

T-203 (plan de trabajo, Control 2): "Subir min_images_per_class a un valor
imposible y verificar con echo $? que el script aborte con exit code != 0".
El test de subprocess de abajo es exactamente ese comando, corrido desde
pytest en vez de a mano.
"""

import json
import subprocess
import sys
from pathlib import Path

from dataset_pipeline.quality_gate.cli import main

FIXTURES = Path(__file__).parent / "fixtures"
COCO = FIXTURES / "coco.two_classes.json"


def test_main_regresa_0_y_reporte_passed_true_cuando_el_umbral_se_cumple(tmp_path):
    output = tmp_path / "quality.json"

    exit_code = main(
        [
            "--coco",
            str(COCO),
            "--policy",
            str(FIXTURES / "quality.pass.yaml"),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["passed"] is True
    assert report["checks"][0]["name"] == "min_images_per_class"
    assert report["checks"][0]["value"] == 1.0


def test_main_regresa_1_cuando_el_umbral_no_se_cumple(tmp_path):
    output = tmp_path / "quality.json"

    exit_code = main(
        [
            "--coco",
            str(COCO),
            "--policy",
            str(FIXTURES / "quality.impossible_threshold.yaml"),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["passed"] is False


# --- SPEC-F4-04: quality.json trae muestras ofensoras, alimentadas por los
# analizadores reales de T-2.2 (Ale), no solo un booleano ---


def test_min_images_per_class_reporta_que_clases_quedaron_por_debajo(tmp_path):
    output = tmp_path / "quality.json"

    main(
        [
            "--coco",
            str(COCO),
            "--policy",
            str(FIXTURES / "quality.impossible_threshold.yaml"),
            "--output",
            str(output),
        ]
    )

    report = json.loads(output.read_text(encoding="utf-8"))
    [check] = [c for c in report["checks"] if c["name"] == "min_images_per_class"]
    # Con el umbral imposible, TODAS las clases del fixture quedan por
    # debajo -> deben aparecer nombradas, no solo el booleano passed=false.
    assert set(check["offending_samples"]) == {"car", "person"}


def test_invalid_boxes_count_se_evalua_y_reporta_las_anotaciones_ofensoras(tmp_path):
    output = tmp_path / "quality.json"

    exit_code = main(
        [
            "--coco",
            str(FIXTURES / "coco.with_invalid_box.json"),
            "--policy",
            str(FIXTURES / "quality.invalid_boxes_fail.yaml"),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    report = json.loads(output.read_text(encoding="utf-8"))
    [check] = [c for c in report["checks"] if c["name"] == "invalid_boxes_count"]
    assert check["passed"] is False
    assert check["value"] == 1.0
    assert check["offending_samples"] == ["1"]


def test_t203_subproceso_real_con_umbral_imposible_termina_con_exit_code_distinto_de_cero(
    tmp_path,
):
    """Es literalmente el comando de verificación de T-203, vía subprocess:
    el proceso del sistema operativo (no una llamada a función en memoria)
    debe morir con código != 0."""
    output = tmp_path / "quality.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dataset_pipeline.quality_gate.cli",
            "--coco",
            str(COCO),
            "--policy",
            str(FIXTURES / "quality.impossible_threshold.yaml"),
            "--output",
            str(output),
        ],
        cwd=Path(__file__).parents[2] / "src",
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0, (
        f"exit={result.returncode}, stdout={result.stdout!r}, stderr={result.stderr!r}"
    )
    assert "BLOQUEA" in result.stdout


def test_t203_subproceso_real_con_umbral_alcanzable_termina_con_exit_code_cero(tmp_path):
    output = tmp_path / "quality.json"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "dataset_pipeline.quality_gate.cli",
            "--coco",
            str(COCO),
            "--policy",
            str(FIXTURES / "quality.pass.yaml"),
            "--output",
            str(output),
        ],
        cwd=Path(__file__).parents[2] / "src",
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, f"stdout={result.stdout!r}, stderr={result.stderr!r}"
    assert "PASA" in result.stdout
