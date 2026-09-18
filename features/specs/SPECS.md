# SPECs — Proyecto 2 (Ruta al Dataset)

Trazabilidad regla de negocio → SPEC → `.feature` → step definitions para
el pipeline Python (`pipeline/`). Es un documento **nuevo**, separado del
`features/SPECS.md` de la raíz (que documenta el Proyecto 1 / portal Node
sobre el que se construye este pipeline) — evita mezclar dos rúbricas y dos
esquemas de numeración de SPEC distintos en el mismo archivo.

Convención de ID: `SPEC-F<frente>-<secuencial>`, ej. `SPEC-F4-01` = Frente 4,
primer SPEC. Los `.feature` viven en `features/specs/`, con nombre
`f<frente>-<secuencial>-<slug>.feature`; sus step definitions en
`pipeline/tests/step_defs/`.

| SPEC ID | Regla de negocio | Frente | Archivo `.feature` | Dueño |
|---|---|---|---|---|
| SPEC-F2-01 | Un COCO malformado (bbox de aridad incorrecta, `category_id`/`image_id` huérfano) se rechaza nombrando el campo exacto | 2 — Validación Pydantic v2 | `f2-01-modelos-coco.feature` | Alejandra |
| SPEC-F2-02 | La configuración de entorno del pipeline falla rápido al arrancar si falta o es inválida, no a mitad de un analizador | 2 — Validación Pydantic v2 | `f2-01-modelos-coco.feature` | Alejandra |
| SPEC-F4-01 | La política vive en `quality.yaml`: cambiar un umbral cambia el resultado de la compuerta sin tocar ningún archivo de código | 4 — Compuerta de calidad | `f4-01-quality-gate.feature` | Juan Pablo |
| SPEC-F4-02 | Un check `severity: fail` que no cumple su umbral bloquea de verdad: el proceso termina con exit code ≠ 0 | 4 — Compuerta de calidad | `f4-01-quality-gate.feature` | Juan Pablo |
| SPEC-F4-03 | Un check `severity: warn` que no cumple se registra en `quality.json` pero nunca bloquea (exit code 0) | 4 — Compuerta de calidad | `f4-01-quality-gate.feature` | Juan Pablo |
| SPEC-F4-04 | `quality.json` nunca es solo un booleano: siempre trae valor observado, umbral, y muestras ofensoras cuando el check las provee | 4 — Compuerta de calidad | `f4-01-quality-gate.feature` | Juan Pablo |

## Notas de Frente 4 (issue #9, T-2.3)

- El contrato de `quality.yaml` (forma: `checks: {nombre: {threshold, severity}}`)
  lo definió y valida Alejandra en `dataset_pipeline.config.quality`
  (`QualityPolicy`/`QualityCheck`) — Frente 4 solo lo consume, no lo
  redefine, para no tener dos fuentes de verdad del mismo esquema.
- La dirección de la comparación por check (¿más alto es mejor, o más
  bajo?) y qué función calcula cada métrica/muestras ofensoras a partir del
  COCO sí es responsabilidad de Frente 4: vive en
  `pipeline/src/dataset_pipeline/quality_gate/evaluator.py`
  (`_CHECK_DIRECTIONS`) y `cli.py` (`_METRIC_COMPUTERS`,
  `_OFFENDER_COMPUTERS`). Un check declarado en `quality.yaml` sin métrica
  registrada truena con `UnknownCheckError` en vez de pasar en silencio —
  a propósito: "una compuerta que nunca bloquea no vale nada".
- **Checks conectados hoy**: `min_images_per_class` (M3, usando
  `coco.stats.images_per_category` de Ale + su analizador
  `analyze_class_imbalance` de T-2.2 para las muestras ofensoras —
  qué clases quedaron por debajo) e `invalid_boxes_count` (usando su
  `analyze_invalid_boxes`, muestras = IDs de anotación degeneradas).
  `duplicates` (T-2.2) no se conectó como check: necesita las imágenes
  reales cargadas en memoria (`PIL.Image`), no solo el COCO JSON, y la
  compuerta de este ticket solo recibe `--coco`; `spatial_bias` es
  descriptivo (percentiles), sin un umbral pass/fail natural — no encaja
  como check de la compuerta. Se documenta aquí en vez de silenciarlo.
- `_METRIC_COMPUTERS`/`_OFFENDER_COMPUTERS` viven en `cli.py`, no en
  `evaluator.py`: son la capa que sabe qué analizador de T-2.2 alimenta
  cada check, mientras que `evaluator.py` solo sabe comparar números — así
  un check nuevo se agrega sin tocar la lógica de comparación.
- Verificación manual de Control 2 (T-203), documentada porque no se puede
  reconstruir después: `python -m dataset_pipeline.quality_gate.cli --coco
  ... --policy ...` con `min_images_per_class` en un valor imposible (ej.
  99999) termina con `echo "exit=$?"` ≠ 0. Cubierto tanto en
  `tests/quality_gate/test_cli.py` (subprocess real) como en el escenario
  Gherkin correspondiente (SPEC-F4-01).
