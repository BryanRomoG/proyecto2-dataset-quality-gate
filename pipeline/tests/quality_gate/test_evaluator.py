"""Frente 4 — el evaluador decide pass/fail por check y el resultado global.

Regla del plan de trabajo: un check `severity: fail` que no cumple el
umbral bloquea la compuerta (overall no pasa); uno `severity: warn` se
reporta pero nunca bloquea. Y "subir el umbral a un valor imposible debe
abortar con exit code distinto de cero" (T-203) — eso se prueba aquí a
nivel de `QualityReport.passed`, y en test_cli.py a nivel de exit code real.
"""

import pytest

from dataset_pipeline.config import QualityCheck, QualityPolicy
from dataset_pipeline.quality_gate.evaluator import UnknownCheckError, evaluate


def _policy(threshold: float, severity: str) -> QualityPolicy:
    return QualityPolicy(
        checks={"min_images_per_class": QualityCheck(threshold=threshold, severity=severity)}
    )


def test_check_fail_que_no_cumple_bloquea_el_reporte_completo():
    policy = _policy(threshold=300, severity="fail")

    report = evaluate(metric_values={"min_images_per_class": 250}, policy=policy)

    [result] = report.checks
    assert result.passed is False
    assert report.passed is False


def test_check_fail_que_cumple_pasa():
    policy = _policy(threshold=300, severity="fail")

    report = evaluate(metric_values={"min_images_per_class": 300}, policy=policy)

    [result] = report.checks
    assert result.passed is True
    assert report.passed is True


def test_check_warn_que_no_cumple_se_reporta_pero_no_bloquea():
    policy = _policy(threshold=300, severity="warn")

    report = evaluate(metric_values={"min_images_per_class": 100}, policy=policy)

    [result] = report.checks
    assert result.passed is False
    # Un warn roto no debe tumbar el resultado GLOBAL de la compuerta.
    assert report.passed is True


def test_umbral_imposible_hace_fallar_incluso_con_dataset_perfecto():
    # T-203: subir min_images_per_class a un valor absurdo debe romper la
    # compuerta pase lo que pase con los datos reales.
    policy = _policy(threshold=99_999, severity="fail")

    report = evaluate(metric_values={"min_images_per_class": 5_000}, policy=policy)

    assert report.passed is False


def test_check_sin_metrica_calculada_lanza_error_con_el_nombre_del_check():
    policy = _policy(threshold=300, severity="fail")

    with pytest.raises(UnknownCheckError, match="min_images_per_class"):
        evaluate(metric_values={}, policy=policy)
