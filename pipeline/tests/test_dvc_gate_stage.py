"""La compuerta de calidad está dentro del pipeline DVC, antes de `split`."""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def _stages() -> dict:
    return yaml.safe_load((REPO_ROOT / "dvc.yaml").read_text(encoding="utf-8"))["stages"]


def test_gate_stage_runs_the_quality_gate_cli_with_the_policy() -> None:
    gate = _stages()["gate"]

    assert "dataset_pipeline.quality_gate.cli" in gate["cmd"]
    assert "quality.yaml" in gate["deps"]


def test_split_depends_on_the_gate_output_so_a_failing_gate_blocks_it() -> None:
    stages = _stages()
    gate_outputs = stages["gate"]["outs"]

    assert gate_outputs
    assert set(gate_outputs) <= set(stages["split"]["deps"])
