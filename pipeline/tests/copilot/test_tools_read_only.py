"""SPEC-F8-01 — ninguna herramienta del Copilot tiene efectos de escritura.

Dos pruebas independientes, a propósito: el análisis estático detecta un
patrón de escritura aunque nunca se ejecute esa rama de código; la prueba
de comportamiento detecta una escritura real aunque el patrón esté
disfrazado (ej. una variable con el nombre del método en vez del literal).
Juntas son más difíciles de burlar por accidente que cualquiera de las dos
sola.
"""

import hashlib
from pathlib import Path

import pytest

from dataset_pipeline.copilot.tools import CopilotToolkit

TOOLS_SOURCE = (
    Path(__file__).parents[2] / "src" / "dataset_pipeline" / "copilot" / "tools.py"
).read_text(encoding="utf-8")

_FORBIDDEN_PATTERNS = [
    '"w")',
    "'w')",
    '"a")',
    "'a')",
    ".write(",
    ".write_text(",
    ".write_bytes(",
    "os.remove",
    "os.unlink",
    "shutil.rmtree",
    "put_object",
    "INSERT ",
    "UPDATE ",
    "DELETE ",
    "requests.post",
    "requests.put",
]


@pytest.mark.parametrize("pattern", _FORBIDDEN_PATTERNS)
def test_tools_source_has_no_write_pattern(pattern: str) -> None:
    assert pattern not in TOOLS_SOURCE, f"patrón de escritura sospechoso en tools.py: {pattern!r}"


def _data_dir_hash(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(data_dir.glob("*.json")):
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_calling_every_tool_leaves_data_files_unchanged(tmp_path: Path) -> None:
    data_dir = Path(__file__).parents[3] / "contracts" / "examples"
    for name in ("quality.json", "splits.json", "versions.json"):
        (tmp_path / name).write_bytes((data_dir / name).read_bytes())

    hash_before = _data_dir_hash(tmp_path)
    toolkit = CopilotToolkit(tmp_path)

    toolkit.get_quality_report()
    toolkit.get_split_counts()
    versions = toolkit.list_dataset_versions()
    toolkit.get_version_diff("v0.1.0", "v0.2.0")
    toolkit.current_version()

    assert versions["current"] == "v0.2.0"
    assert _data_dir_hash(tmp_path) == hash_before
