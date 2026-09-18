"""Placeholder — RED: solo registra los escenarios, sin implementar steps."""

from pathlib import Path

from pytest_bdd import scenarios

REPO_ROOT = Path(__file__).parents[3]
FEATURE_FILE = REPO_ROOT / "features" / "specs" / "f10-02-mutacion.feature"

scenarios(str(FEATURE_FILE))
