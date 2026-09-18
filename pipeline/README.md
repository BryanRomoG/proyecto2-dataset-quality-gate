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

## Contenido (Frente 3 — T-2.2)

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

## Contenido (Frente 5 — T-3.1)

`src/dataset_pipeline/splits/stratified.py` — split train/val/test
estratificado, reproducible por semilla y sin fuga de near-duplicates:

- **Estratificado**: agrupa imágenes por "firma" (el conjunto de clases que
  contienen) y reparte cada grupo proporcionalmente — así cada combinación
  de clases queda representada en las tres particiones, no solo la más
  común.
- **Reproducible**: usa `random.Random(seed)` sobre listas siempre
  ordenadas antes de barajar (nunca la iteración de un `set`/`dict`, que no
  está garantizada) — dos corridas con la misma semilla dan exactamente la
  misma asignación (verificado con un script independiente, no solo el
  test).
- **Cero fuga**: los pares de near-duplicates de `find_duplicate_pairs`
  (T-2.2) se resuelven con union-find en clusters — todas las imágenes de
  un cluster van siempre al mismo split, aunque eso rompa un poco la
  proporción exacta de ese grupo.

Specs en `features/specs/f5-01-splits.feature`, con step definitions en
`tests/step_defs/test_f5_01_splits.py`.

**Pendiente antes de cerrar el ticket (parte del DoD):** correr esto contra
el COCO real del portal una vez cerrada la anotación (T-201) y documentar
el resultado — con datos sintéticos ya está probado, pero el DoD pide la
verificación contra datos reales.

Fuera de alcance: el pipeline DVC que versiona estos splits (Frente 6,
T-3.2).

## Contenido (Frente 6 — T-3.2)

Pipeline DVC real (`dvc.yaml` en la raíz del repo), 3 etapas con deps/outs
propios — no una sola etapa monolítica (ver `dvc dag`):

```
data/raw/coco.json.dvc ──┐
                          ├─> validate ──┐
data/raw/images.dvc ─────┼──────────────┼─> analyze ──> split
                          └──────────────┘
```

- **validate**: carga y valida el COCO (T-1.3) → `coco.validated.json`.
- **analyze**: corre los 5 analizadores (T-2.2) contra el COCO validado y
  las imágenes en `data/raw/images/`, usando el umbral `min_images_per_class`
  de `quality.yaml` (nunca hardcodeado) → `quality_metrics.json`.
- **split**: genera train/val/test (T-3.1), usando los pares de pHash que
  ya calculó `analyze` para garantizar cero fuga → `splits.json`.

**Setup necesario, una vez por máquina** (`.dvc/config.local`, nunca se
versiona): el cache de DVC se saca de la carpeta sincronizada por OneDrive
para evitar los mismos bloqueos de archivo que ya vimos con Git —
si tu repo no vive en OneDrive, este paso no aplica:

```bash
dvc cache dir C:/dvc-cache --local
dvc remote modify --local dev access_key_id minioadmin
dvc remote modify --local dev secret_access_key minioadmin
```

**Datos de muestra**, mientras T-101 (contratos congelados) y la
integración real con el export del portal no existan — genera un COCO
pequeño con imágenes sintéticas reales (incluye un duplicado deliberado
para que `analyze` tenga algo real que detectar):

```bash
python pipeline/scripts/generate_sample_coco.py \
  --images-per-class 15 --out data/raw/coco.json --images-dir data/raw/images
dvc add data/raw/coco.json data/raw/images
```

**Correr el pipeline:**

```bash
dvc repro          # primera vez: corre las 3 etapas
dvc repro          # segunda vez: "Data and pipelines are up to date" — nada se rehace
dvc dag            # confirma que son 3 etapas separadas, no una
```

Verificado con evidencia real (no solo el test): dos corridas consecutivas
de `dvc repro` no rehacen nada; modificar solo `splits.yaml` rehace
únicamente la etapa `split`; `git ls-files data/` no incluye ningún
`.jpg`/`.png`/`.parquet` de nuestros datos (si aparece algo, es de los
seed-assets de Proyecto 1, preexistente — ver nota abajo).

**Remotes DEV (MinIO) y PROD (S3):**

```bash
docker compose up -d minio
# una sola vez: crear el bucket, MinIO no lo hace solo
docker exec <container_minio> sh -c "mc alias set local http://localhost:9000 minioadmin minioadmin && mc mb local/dvc-dataset"

dvc push -r dev              # sube el cache al MinIO real
dvc status -r dev            # documentado abajo (parte del DoD)
dvc status -r prod           # sin cuenta de AWS real: falla limpio, es lo esperado
```

**Verificado en vivo en esta sesión** (no solo simulado):
- `dvc push -r dev` → `36 files pushed` contra un MinIO real levantado con
  `docker compose up -d minio`.
- Cache local vaciado por completo y `dvc pull -r dev` → `36 files fetched`;
  el md5 de `data/raw/coco.json` después del pull coincide exactamente con
  el de antes de vaciar el cache — round-trip real, no solo un conteo.
- `dvc status -r dev` → `Cache and remote 'dev' are in sync.`
- `dvc status -r prod` → `ERROR: unexpected error - Unable to locate
  credentials` — esperado y documentado: no hay cuenta de AWS real todavía
  (mismo caso que el riesgo ya aceptado en el plan para el Frente 9/Terraform:
  se califica el código y la configuración del remote, no un despliegue en
  vivo contra PROD).

**Releases y diff entre versiones:**

```bash
python pipeline/scripts/release.py v1.0.0 -m "Primer release del dataset"
python pipeline/scripts/diff_release.py v0.9.0 v1.0.0   # imágenes/cajas añadidas, clases bajo el mínimo
```

**Nota sobre `.jpg` en `git ls-files`:** existen 3 en
`server/src/db/seed-assets/` — son fixtures de semilla de Proyecto 1
(`npm run db:seed`), preexistentes desde el commit base, no parte del
dataset de este proyecto. El chequeo de "datos fuera de Git" de T-3.2 se
refiere a `data/` (donde sí está limpio), no a esos.

Specs en `features/specs/f6-01-dvc-pipeline.feature`. El escenario de
mismo hash DEV/PROD está marcado `@requiere_minio` y se salta solo si no
hay remote alcanzable — no es opcional, es honesto: no hay forma de
probar contra infraestructura real sin infraestructura real corriendo.
