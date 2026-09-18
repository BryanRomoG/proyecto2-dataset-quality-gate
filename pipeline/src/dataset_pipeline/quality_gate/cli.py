"""Compuerta de calidad (Frente 4): ata ingesta + política + evaluador.

    python -m dataset_pipeline.quality_gate.cli \
        --coco dataset.json --policy quality.yaml --output quality.json

Exit code 0 si todos los checks `severity: fail` pasan; 1 si alguno no
pasa. Los `severity: warn` nunca cambian el exit code — solo se reportan.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

from dataset_pipeline.analyzers import analyze_class_imbalance, analyze_invalid_boxes
from dataset_pipeline.coco.loader import load_coco_dataset
from dataset_pipeline.coco.models import CocoDataset
from dataset_pipeline.coco.stats import images_per_category
from dataset_pipeline.config import QualityPolicy, load_quality_policy
from dataset_pipeline.quality_gate.evaluator import QualityReport, evaluate
from dataset_pipeline.quality_gate.metrics import min_images_per_class


def _invalid_boxes_count(dataset: CocoDataset) -> float:
    return float(len(analyze_invalid_boxes(dataset).invalid))


def _min_images_per_class_offenders(dataset: CocoDataset, threshold: float) -> list[str]:
    # Reusa el analizador de desbalance de clases (T-2.2, Ale) para nombrar
    # las clases concretas que quedaron por debajo del umbral, en vez de
    # solo reportar "el mínimo fue X" sin decir a qué clase pertenece.
    counts = images_per_category(dataset)
    report = analyze_class_imbalance(counts, min_images_per_class=int(threshold))
    return report.classes_below_minimum


def _invalid_boxes_offenders(dataset: CocoDataset, _threshold: float) -> list[str]:
    return [str(box.annotation_id) for box in analyze_invalid_boxes(dataset).invalid]


# Cada check de quality.yaml necesita un cómputo de VALOR registrado aquí.
# Un check sin analizador todavía (ej. algo del Frente 3 que no ha
# aterrizado) hace que evaluate() truene con UnknownCheckError en vez de
# pasar en silencio.
_METRIC_COMPUTERS: dict[str, Callable[[CocoDataset], float]] = {
    "min_images_per_class": min_images_per_class,
    "invalid_boxes_count": _invalid_boxes_count,
}

# Y, opcionalmente, un cómputo de MUESTRAS OFENSORAS (SPEC-F4-04) — un check
# sin entrada aquí simplemente reporta lista vacía, no es un error.
_OFFENDER_COMPUTERS: dict[str, Callable[[CocoDataset, float], list[str]]] = {
    "min_images_per_class": _min_images_per_class_offenders,
    "invalid_boxes_count": _invalid_boxes_offenders,
}


def _compute_metric_values(dataset: CocoDataset, policy: QualityPolicy) -> dict[str, float]:
    values: dict[str, float] = {}
    for name in policy.checks:
        computer = _METRIC_COMPUTERS.get(name)
        if computer is not None:
            values[name] = computer(dataset)
    return values


def _compute_offending_samples(dataset: CocoDataset, policy: QualityPolicy) -> dict[str, list[str]]:
    samples: dict[str, list[str]] = {}
    for name, check in policy.checks.items():
        computer = _OFFENDER_COMPUTERS.get(name)
        if computer is not None:
            samples[name] = computer(dataset, check.threshold)
    return samples


def run(coco_path: str | Path, policy_path: str | Path) -> QualityReport:
    dataset = load_coco_dataset(coco_path)
    policy = load_quality_policy(policy_path)
    metric_values = _compute_metric_values(dataset, policy)
    offending_samples = _compute_offending_samples(dataset, policy)
    return evaluate(metric_values, policy, offending_samples=offending_samples)


def _report_to_json(report: QualityReport) -> dict:
    return {
        "passed": report.passed,
        "checks": [
            {
                "name": check.name,
                "value": check.value,
                "threshold": check.threshold,
                "direction": check.direction,
                "severity": check.severity,
                "passed": check.passed,
                "offending_samples": check.offending_samples,
            }
            for check in report.checks
        ],
    }


def _print_summary(report: QualityReport) -> None:
    for check in report.checks:
        status = "PASS" if check.passed else check.severity.upper()
        print(f"[{status}] {check.name}: {check.value} ({check.direction} {check.threshold})")
    print("COMPUERTA: PASA" if report.passed else "COMPUERTA: BLOQUEA")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compuerta de calidad del dataset (Frente 4)")
    parser.add_argument("--coco", required=True, help="Ruta al COCO exportado del portal")
    parser.add_argument("--policy", default="quality.yaml", help="Ruta a quality.yaml")
    parser.add_argument("--output", default="quality.json", help="Ruta de salida del reporte")
    args = parser.parse_args(argv)

    report = run(args.coco, args.policy)
    Path(args.output).write_text(json.dumps(_report_to_json(report), indent=2), encoding="utf-8")
    _print_summary(report)

    return 0 if report.passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
