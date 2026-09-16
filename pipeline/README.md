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

## Contenido (Frente 3 — T-202)

Cinco analizadores en `src/dataset_pipeline/analyzers/`, todos funciones
puras: reciben datos como parámetro (dataset, conteos, imágenes ya cargadas
o una lista de áreas) y devuelven un reporte Pydantic — ninguno abre
conexiones, lee `os.environ` ni el `quality.yaml` por su cuenta (eso es
trabajo de quien los invoque, la compuerta del Frente 4/T-203).

- `small_objects.py` (SPEC-F3-01): % de objetos bajo un umbral de píxeles
  configurable, clase más afectada, muestras.
- `class_imbalance.py` (SPEC-F3-02): ratio mayoría/minoría y clases por
  debajo del mínimo, sobre conteos de *imágenes* por clase (no de cajas) —
  ver `coco/stats.py::images_per_category`, misma regla de conteo que M3.
- `duplicates.py` (SPEC-F3-03): near-duplicates por pHash (`imagehash`),
  detecta una copia recomprimida que un hash exacto (MD5/SHA) no vería.
- `invalid_boxes.py` (SPEC-F3-04): width/height negativo, caja fuera de los
  límites de la imagen, `area` incoherente con `width*height`.
- `spatial_bias.py` (SPEC-F3-05): media, mediana y percentiles (p10/p25/p75/
  p90) — nunca solo la media.

Specs en `features/specs/f3-01-*.feature` … `f3-05-*.feature`, con step
definitions en `tests/step_defs/`.

**Pendiente antes de cerrar el ticket (parte del DoD, no de este código):**
el DoD pide que alguien del equipo recalcule a mano cada métrica sobre un
COCO real exportado del portal y confirme que coincide con lo que reportan
estos analizadores — eso requiere datos reales (300+ imágenes/clase) que
todavía no existen; hacerlo en cuanto la anotación esté más avanzada, antes
de que lo haga el evaluador.

Fuera de alcance: la compuerta que decide warn/fail sobre estos resultados
(Frente 4, T-203).
