# dataset-pipeline

Pipeline Python de calidad y versionado de datasets (Proyecto 2). Vive separado
de `client/` y `server/` (el monolito Node del portal de anotación) y consume
el COCO que ese portal exporta.

## Setup

```bash
cd pipeline
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

## Contenido (Frente 2 — T-1.3)

- `src/dataset_pipeline/coco/models.py` — modelos Pydantic v2 del COCO
  (`CocoDataset`, `CocoImage`, `CocoAnnotation`, `CocoCategory`), reflejando
  uno a uno los esquemas Zod de `server/src/export/coco.schema.ts`. Un COCO
  mal formado se rechaza nombrando el campo (bbox con aridad incorrecta,
  `category_id` inexistente, `image_id` huérfano) en vez de un traceback
  crudo. Usa `field_validator`, `model_validator` y `ConfigDict` reales de
  Pydantic v2 (nada de la sintaxis de la versión anterior).
- `src/dataset_pipeline/config/` — validación con **pydantic-settings**:
  - `settings.py`: variables de entorno del pipeline (`PipelineSettings`),
    falla rápido al arrancar si falta `UPLOAD_MAX_BYTES` o no es numérico.
  - `quality.py` / `splits.py`: esquema de `quality.yaml` y de la config de
    splits — el `dict` crudo de `yaml.safe_load()` nunca se usa directo,
    siempre pasa por el modelo Pydantic correspondiente.
- `features/specs/f2-01-modelos-coco.feature` (en la raíz del repo) — los 4
  escenarios de Gherkin de SPEC-F2-01/02, con sus step definitions en
  `tests/step_defs/`.

Fuera de alcance (Frente 3, otro ticket): los analizadores que consumen
estos modelos.
