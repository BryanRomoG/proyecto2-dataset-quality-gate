"""Herramientas de solo lectura que el Copilot expone (T-3.3, issue #14).

SPEC-F8-01: ninguna función de este módulo escribe — ni al disco (archivo
de datos), ni a una base de datos, ni sube objetos a MinIO/S3. Cada método
abre un contrato congelado en modo lectura y lo valida con
`copilot.contracts`; jamás modifica ni sube nada.
`tests/copilot/test_tools_read_only.py` prueba esto de dos formas: análisis
estático del código fuente (ningún patrón de escritura) y una prueba de
comportamiento (invocar cada herramienta y comprobar que el contenido de
los archivos de datos no cambió).

`CopilotToolkit` no elige el proveedor del LLM ni decide cuándo se llaman
estas herramientas — eso es responsabilidad de `copilot.agent`. Aquí solo
vive el acceso a los datos, para poder probarlo sin depender de ningún LLM.
"""

from pathlib import Path

from dataset_pipeline.copilot.contracts import load_quality, load_splits, load_versions


class UnknownVersionDiffError(Exception):
    """Se pidió el diff entre dos versiones que no está registrado en
    versions.json — el Copilot debe admitir que no lo sabe, no inventarlo."""


class CopilotToolkit:
    def __init__(self, data_dir: Path | str):
        self.data_dir = Path(data_dir)

    def get_quality_report(self) -> dict:
        """Último reporte de la compuerta de calidad: qué checks pasaron,
        con qué valor observado, umbral, severidad y muestras ofensoras."""
        report = load_quality(self.data_dir / "quality.json")
        return report.model_dump()

    def get_split_counts(self) -> dict:
        """Cuántas imágenes cayeron en train/val/test, con qué semilla y
        proporciones se generó el split."""
        splits = load_splits(self.data_dir / "splits.json")
        return splits.model_dump()

    def list_dataset_versions(self) -> dict:
        """Versiones publicadas del dataset (tag, mensaje, fecha de
        creación) y cuál es la versión actual (`current`)."""
        versions = load_versions(self.data_dir / "versions.json")
        return {
            "current": versions.current,
            "releases": [
                {
                    "version": release.version,
                    "message": release.message,
                    "created_at": release.created_at.isoformat(),
                }
                for release in versions.releases
            ],
        }

    def get_version_diff(self, from_version: str, to_version: str) -> dict:
        """Qué cambió entre dos versiones del dataset: imágenes y cajas
        agregadas o quitadas, y qué clases quedaron por debajo del mínimo."""
        versions = load_versions(self.data_dir / "versions.json")
        for release in versions.releases:
            diff = release.diff_vs_previous
            if diff is None:
                continue
            if diff.from_version == from_version and diff.to_version == to_version:
                return diff.model_dump(by_alias=True)
        raise UnknownVersionDiffError(
            f"no hay un diff registrado de {from_version} a {to_version} en versions.json"
        )

    def current_version(self) -> str:
        """La versión actual del dataset (`versions.json:current`). No es
        una herramienta expuesta al LLM: la usa `copilot.agent` para citar
        la versión en cada respuesta sin depender de que el modelo la
        mencione por su cuenta."""
        return load_versions(self.data_dir / "versions.json").current
