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
| SPEC-F8-01 | Ninguna herramienta del Copilot tiene efectos de escritura (ni al disco, ni a una BD, ni sube objetos a MinIO/S3) | 8 — Dataset Copilot | `f8-01-copilot.feature` | Juan Pablo |
| SPEC-F8-02 | Una respuesta con cifras trae la traza completa de qué herramienta se llamó y qué devolvió | 8 — Dataset Copilot | `f8-01-copilot.feature` | Juan Pablo |
| SPEC-F8-03 | La respuesta cambia si cambia la fuente de datos (no hay caché ni cifras fijas en el prompt) | 8 — Dataset Copilot | `f8-01-copilot.feature` | Juan Pablo |
| SPEC-F8-04 | El Copilot admite no saber en vez de inventar una cifra cuando ninguna herramienta cubre la pregunta | 8 — Dataset Copilot | `f8-01-copilot.feature` | Juan Pablo |
| SPEC-F8-05 | Toda respuesta que usó al menos una herramienta cita la versión actual del dataset | 8 — Dataset Copilot | `f8-01-copilot.feature` | Juan Pablo |
| SPEC-F8-06 | Un error del proveedor del LLM se maneja y nunca sale como traceback de Python | 8 — Dataset Copilot | `f8-01-copilot.feature` | Juan Pablo |

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

## Notas de Frente 8 (issue #14, T-3.3) — Dataset Copilot

- **Alcance de "servidor MCP puro"**: se construyó el servidor MCP real
  (`copilot/mcp_server.py`, protocolo por stdio, probado con el SDK
  cliente de verdad en `tests/copilot/test_mcp_server_protocol.py`) más un
  loop de orquestación (`copilot/agent.py`) que un LLM real puede usar
  contra esas mismas herramientas. Lo que **no** se construyó a propósito
  es un cliente de chat interactivo para humanos (CLI/UI) — eso es
  responsabilidad de quien integre el Copilot en un producto (Frente 7,
  fuera de alcance según el propio issue #14); aquí la evidencia de "el
  agente responde bien" son las pruebas automatizadas, no una demo manual.
- **Cuatro herramientas, todas de solo lectura**, sobre los contratos
  congelados de T-1.1 (`contracts/examples/{quality,splits,versions}.json`,
  issue #27): `get_quality_report`, `get_split_counts`,
  `list_dataset_versions`, `get_version_diff`. Viven como métodos de
  `CopilotToolkit` (`copilot/tools.py`) y se registran tal cual en el
  servidor MCP (`mcp.tool()`) — una sola definición, nunca dos esquemas
  que se puedan desincronizar.
- **Function calling manual, no automático**: el SDK de Google (`google-genai`)
  ofrece resolver las llamadas a herramientas automáticamente, pero eso
  esconde la traza dentro del cliente. Se usó
  `automatic_function_calling.disable=True` a propósito, para que
  `copilot/agent.py` controle el loop y pueda construir la traza exacta
  que pide SPEC-F8-02 (qué herramienta, con qué argumentos, qué devolvió).
- **La versión del dataset se cita de forma estructural, no confiando en
  el texto del LLM**: `agent.py` toma `toolkit.current_version()`
  directamente de `versions.json` después de cualquier tool call, en vez
  de esperar que el modelo la mencione correctamente en su respuesta.
  Mismo principio que la búsqueda SQL-only del Proyecto 1: una garantía
  probable determinísticamente le gana a una que depende del criterio
  (probabilístico) del modelo.
- **Elección de proveedor**: Gemini (capa gratuita de Google AI Studio),
  decidido junto con el equipo por costo — Anthropic/OpenAI no tienen capa
  gratuita permanente para su API. La cuenta usada es personal del
  desarrollador, no del equipo.
- **Bug real encontrado en desarrollo, no en el código propio**: el modelo
  por defecto usado inicialmente (`gemini-2.5-flash`, y luego el alias
  `gemini-flash-latest`) falló en pruebas en vivo reales — el primero con
  `404 NOT_FOUND` ("ya no disponible para nuevos usuarios"), el segundo con
  `503 UNAVAILABLE` ("alta demanda") de forma consistente en dos intentos.
  Se resolvió fijando `gemini-3.5-flash-lite` como modelo por defecto
  (`copilot/settings.py`), verificado con una llamada real end-to-end
  (`tests/copilot/test_live_gemini_smoke.py`, se salta si no hay
  `GEMINI_API_KEY`). Documentado aquí porque un proveedor externo puede
  volver a retirar un modelo sin aviso — si eso rompe el Copilot en el
  futuro, este es el motivo más probable, y `GEMINI_MODEL` en `.env` se
  puede cambiar sin tocar código.
- **El 503 de arriba no era un capricho del modelo elegido, sino la capa
  gratuita saturándose bajo carga** — así que además de fijar un modelo
  más estable, `GeminiClient` reintenta con cooldown (backoff exponencial
  + jitter, 3 intentos por defecto) cualquier 429 (cuota agotada) o 5xx
  (sobrecarga/mantenimiento) que el SDK reporte como
  `google.genai.errors.APIError`. Un 404/400 (modelo inexistente, API key
  inválida) nunca se reintenta: no es un problema transitorio, es una
  configuración que hay que corregir a mano, y reintentarlo solo tarda más
  en fallar. Probado sin red real en `tests/copilot/test_llm_retry.py`,
  fabricando los mismos errores que devuelve el SDK contra un chat falso
  y con la función `sleep` inyectada (no duerme de verdad en tests).
- **`mcp` SDK 2.x renombró `FastMCP` a `MCPServer`** entre lo documentado
  en tutoriales públicos (basados en 1.x) y la versión instalada
  (`mcp==2.2.0`); se detectó de inmediato porque el import fallaba con un
  mensaje explícito de migración del propio paquete, no en silencio.
- Los 3 escenarios obligatorios de la rúbrica (traza visible, cambia con
  la fuente, admite no saber) y los otros 3 del Gherkin del ticket (solo
  lectura, cita versión, manejo de errores) están cubiertos de forma
  determinística contra un doble de LLM
  (`tests/copilot/fakes.py`,`features/specs/f8-01-copilot.feature`), sin
  red ni costo ni no-determinismo. La evidencia contra el proveedor real
  vive aparte (`test_live_gemini_smoke.py`) precisamente para no depender
  de la disponibilidad de Gemini para que el CI pase.
