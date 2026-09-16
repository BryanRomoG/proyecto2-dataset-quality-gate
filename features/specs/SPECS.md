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
| SPEC-F4-01 | Un check `severity: fail` que no cumple su umbral bloquea la compuerta (exit code ≠ 0); uno que sí cumple la deja pasar (exit code 0). Un umbral imposible bloquea incluso un dataset saludable (T-203, Control 2) | 4 — Compuerta de calidad | `f4-01-quality-gate.feature` | Juan Pablo |
| SPEC-F4-02 | Un check `severity: warn` que no cumple se reporta individualmente como no cumplido, pero nunca bloquea el resultado global de la compuerta | 4 — Compuerta de calidad | `f4-01-quality-gate.feature` | Juan Pablo |

## Notas de Frente 4

- El contrato de `quality.yaml` (forma: `checks: {nombre: {threshold, severity}}`)
  lo definió y valida Alejandra en `dataset_pipeline.config.quality`
  (`QualityPolicy`/`QualityCheck`) — Frente 4 solo lo consume, no lo
  redefine, para no tener dos fuentes de verdad del mismo esquema.
- La dirección de la comparación por check (¿más alto es mejor, o más
  bajo?) y qué función calcula cada métrica a partir del COCO sí es
  responsabilidad de Frente 4: vive en
  `pipeline/src/dataset_pipeline/quality_gate/evaluator.py`
  (`_CHECK_DIRECTIONS`) y `cli.py` (`_METRIC_COMPUTERS`). Un check declarado
  en `quality.yaml` sin métrica registrada truena con `UnknownCheckError`
  en vez de pasar en silencio — a propósito: "una compuerta que nunca
  bloquea no vale nada".
- Verificación manual de Control 2 (T-203), documentada porque no se puede
  reconstruir después: `python -m dataset_pipeline.quality_gate.cli --coco
  ... --policy ...` con `min_images_per_class` en un valor imposible (ej.
  99999) termina con `echo "exit=$?"` ≠ 0. Cubierto tanto en
  `tests/quality_gate/test_cli.py` (subprocess real) como en el escenario
  Gherkin correspondiente.
