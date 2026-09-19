# dataset-pipeline

Pipeline Python de calidad y versionado de datasets (Proyecto 2). Vive separado
de `client/` y `server/` (el monolito Node del portal de anotación) y consume
el COCO que ese portal exporta.

## Entorno Python (3.12 + lockfile)

El proyecto exige Python 3.12 (`requires-python = ">=3.12"`, `.python-version`) y el CI instala las
versiones exactas de `pipeline/requirements.lock`:

```bash
uv venv --python 3.12 .venv            # o cualquier Python 3.12
uv pip install -r pipeline/requirements.lock && uv pip install --no-deps -e pipeline
# regenerar el lock tras cambiar dependencias:
uv pip compile pipeline/pyproject.toml --extra dev --python-version 3.12 -o pipeline/requirements.lock
```

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
- `invalid_boxes.py` (SPEC-F3-04): width/height negativo o igual a cero, caja
  fuera de los límites de la imagen, `area` incoherente con `width*height`.
- `spatial_bias.py` (SPEC-F3-05): media, mediana y percentiles (p10/p25/p75/
  p90) — nunca solo la media.

Specs en `features/specs/f3-01-*.feature` … `f3-05-*.feature`, con step
definitions en `tests/step_defs/`.

**Verificado contra datos reales (cierra el DoD de T-2.2):** se recalcularon
con un script independiente las cinco métricas sobre el COCO real del portal
(369 imágenes, 1465 cajas) y coinciden exactamente con lo que reportan estos
analizadores: objetos pequeños 74/1465 = 5.05 %; imágenes por clase `car` 317
/ `person` 362 (ratio 1.1420); área de las cajas con media 14478.3, mediana
8316.0 y percentiles p10 1638.0 / p25 3472.0 / p75 17216.0 / p90 34391.0;
0 cajas inválidas; 0 pares near-duplicate (pHash ≤ 8). También coincidieron
sobre el primer lote real de 100 imágenes.

Correr contra datos reales destapó tres defectos que la muestra sintética no
mostraba, ya corregidos (PR #34): las cajas con ancho o alto igual a 0 no se
detectaban; las categorías sin ninguna anotación (`dog`, `bicycle`, sembradas
por el portal) contaban como 0 y dejaban `min_images_per_class` en 0; y un
ratio infinito se escribía como `Infinity`, que no es JSON estándar.

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

**Verificado contra datos reales (cierra el DoD de T-3.1):** sobre las 369
imágenes reales con `seed: 42`, train/val/test = 258/55/56 (suman 369, los
tres conjuntos son disjuntos). Estratificado por clase: `car` 70/15/15 %
(222/47/48) y `person` 70/15/15 % (253/54/55); las dos clases están en val y
test. Dos corridas con la misma semilla producen archivos idénticos (mismo
md5). El dataset no tiene pares near-duplicate, así que ninguno cruza splits;
la garantía de cero fuga la cubren los tests con pares sintéticos.

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

**Datos de muestra** (solo para pruebas locales en una copia del repo):
genera un COCO pequeño con imágenes sintéticas (incluye un duplicado
deliberado para que `analyze` tenga algo real que detectar).

> ⚠️ **No lo corras sobre este checkout:** `dvc add` reemplaza `data/raw`, y
> el dataset versionado en `main` ya es el **real** (369 imágenes), no la
> muestra. Para recuperar el real: `dvc pull -r prod`.

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
dvc status -c -r prod        # compara el cache local contra el bucket S3 real de PROD
```

**Verificado en vivo en esta sesión** (no solo simulado):
- `dvc push -r dev` → `36 files pushed` contra un MinIO real levantado con
  `docker compose up -d minio`.
- Cache local vaciado por completo y `dvc pull -r dev` → `36 files fetched`;
  el md5 de `data/raw/coco.json` después del pull coincide exactamente con
  el de antes de vaciar el cache — round-trip real, no solo un conteo.
- `dvc status -r dev` → `Cache and remote 'dev' are in sync.`
- `dvc status -c -r prod` → `Cache and remote 'prod' are in sync.` contra el
  bucket S3 real `s3://proyecto2-dataset-quality-gate-prod` (región
  `us-east-2`). Ver la sección T-3.2b: hay cuatro `dvc push -r prod` reales y un
  `dvc pull` desde un clon nuevo devolvió el dataset completo.

**Releases y diff entre versiones:** cada cambio de los punteros de datos en
`main` es una versión con tag semver (`git tag -l -n1`):

| Tag | Qué contiene |
|---|---|
| `v0.1.0` | primer lote real (Ale): 100 imágenes, 456 cajas |
| `v0.2.0` | + lote de Juan Pablo: 200 imágenes |
| `v0.3.0` | + lote de Josué y la reserva: 330 imágenes |
| `v1.0.0` | release final: 369 imágenes, `car` 317 / `person` 362; la compuerta pasa |

```bash
python pipeline/scripts/release.py v1.1.0 -m "Descripción"   # dvc push + git tag anotado (árbol limpio)
python pipeline/scripts/diff_release.py v0.3.0 v1.0.0 --remote prod
```

El diff reporta imágenes y cajas añadidas/quitadas, imágenes por clase, clases
bajo el mínimo, **clases que salieron del mínimo** y el **cambio en el porcentaje
de objetos pequeños** (lógica en `coco/diff.py`, con pruebas). Con `--remote
prod` porque las versiones anteriores solo viven en S3. Ejemplo real,
`v0.3.0 → v1.0.0`: +39 imágenes, +183 cajas, −16 cajas (las de `bicycle`
descartadas con `drop_category.py`) y objetos pequeños de 3.47 % a 5.05 %.

**Nota sobre `.jpg` en `git ls-files`:** existen 3 en
`server/src/db/seed-assets/` — son fixtures de semilla de Proyecto 1
(`npm run db:seed`), preexistentes desde el commit base, no parte del
dataset de este proyecto. El chequeo de "datos fuera de Git" de T-3.2 se
refiere a `data/` (donde sí está limpio), no a esos.

Specs en `features/specs/f6-01-dvc-pipeline.feature`. El escenario de
mismo hash DEV/PROD está marcado `@requiere_minio` y se salta solo si no
hay remote alcanzable — no es opcional, es honesto: no hay forma de
probar contra infraestructura real sin infraestructura real corriendo.

## Contenido (Frente 6 — T-3.2b)

El remote `prod` (S3) es el dataset compartido real del equipo — a
diferencia de `dev` (MinIO), que es solo local a cada máquina y nunca sirve
para colaborar. Cada persona sigue anotando en su propio portal local
(su propia MariaDB/MinIO vía `docker compose up -d`, sin cambios); lo que se
comparte vía `prod` es el dataset ya exportado (`data/raw/coco.json` +
`data/raw/images/`).

**Autenticación**: usuarios IAM con access key por persona (no SSO/Identity
Center — el equipo parte de una cuenta AWS nueva, sin una AWS Organization
ya armada por nadie más, así que IAM directo es lo más rápido de
provisionar). Cada quien tiene su propio usuario dentro del grupo
`mlops-p2-team`, con una policy acotada solo al bucket `prod`
(`s3://proyecto2-dataset-quality-gate-prod`) — nadie tiene acceso al resto
de la cuenta.

**Setup por máquina, una sola vez** (no viaja con git):

1. Pide tu access key (Access Key ID + Secret Access Key) a quien
   administra la cuenta AWS del equipo — te la manda por correo, una key
   solo para ti, nunca compartida con nadie más.
2. Instala el AWS CLI:
   - **Windows**: descarga
     https://awscli.amazonaws.com/AWSCLIV2.msi y ábrelo (pide permisos de
     administrador). Si `winget` funciona en tu máquina, alternativamente:
     `winget install -e --id Amazon.AWSCLI`.
   - **macOS**: `brew install awscli` (o el `.pkg` oficial).
   - **Linux**: ver https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html.
   - Verifica con `aws --version` (cierra y abre la terminal si acabas de instalar).
3. Carga tu key (nunca la pegues en un chat que no sea tú tecleándola):
   ```bash
   aws configure --profile mlops-p2
   # Access Key ID: <la tuya>
   # Secret Access Key: <la tuya>
   # Default region name: us-east-1
   # Default output format: json
   ```
4. Verifica que quedó activa (no expone el secret):
   ```bash
   aws sts get-caller-identity --profile mlops-p2
   ```
5. Instala el pipeline y vincula DVC con tu perfil:
   ```bash
   cd pipeline && pip install -e ".[dev]"   # ya trae dvc[s3] (pyproject.toml)
   cd ..
   dvc remote modify --local prod profile mlops-p2   # va a .dvc/config.local, nunca se versiona
   ```

**Cada vez que se retoma trabajo** (sesión nueva — un access key IAM no
expira como una sesión SSO, así que normalmente no hace falta repetir el
login; solo si `aws sts get-caller-identity` falla):

```bash
docker compose up -d                      # portal local: :3000 (npm run dev) o :3100 (docker compose up --build)
dvc pull -r prod                          # trae lo que subieron los demás
dvc checkout --force
```

**Anotar y exportar tu lote** (cada contribuidor, en su propio portal
local — `docker compose up -d` + `npm run dev`, ver README raíz):

1. Sube y anota tus imágenes normalmente en `http://localhost:3000`.
   ⚠️ Usa exactamente los nombres de categoría acordados por el equipo
   (p. ej. `car` y `person`, en minúsculas) — `merge.py` unifica
   categorías por nombre exacto; `"Car"` con mayúscula crea una categoría
   duplicada en vez de sumarse a la existente.
2. Exporta el JSON: botón "COCO" en el portal (`GET /api/export/coco`).
3. Exporta las imágenes: no hay endpoint de descarga masiva en la app
   todavía, así que se bajan directo de MinIO — consola web en
   `http://localhost:9001` (usuario/password de tu `.env`,
   `MINIO_ACCESS_KEY`/`MINIO_SECRET_KEY`) y descarga el contenido del
   bucket (`MINIO_BUCKET`, default `annotation-images`). Alternativa con
   el cliente `mc`: `mc mirror local/annotation-images ./mi-lote/`.
   El `file_name` de cada imagen en el JSON es el nombre del objeto en
   MinIO sin la carpeta (`<uuid>-nombre.jpg`), así que copia el
   contenido de la carpeta `images/` que baja (los archivos, no la
   carpeta) directo a `data/raw/images/`: los nombres ya coinciden y el
   UUID evita choques si dos personas subieron un `image.jpg`.
4. Comparte el `.json` + la carpeta de imágenes con quien vaya a fusionar
   los lotes (Drive, zip, USB — logística de equipo, no de la app).

**Fusionar el lote de otro contribuidor sin colisión de IDs** (T-3.2b,
`pipeline/src/dataset_pipeline/coco/merge.py`): dos exports independientes
del portal (`GET /api/export/coco`) siempre van a reusar los mismos rangos
de id porque cada MariaDB local cuenta desde su propio cero — fusionarlos
tal cual produciría `image_id`/`annotation_id` duplicados. `merge.py`
resuelve esto reasignando los ids del lote entrante a partir del máximo ya
usado en el base, y unificando categorías por nombre (no por id numérico):

```bash
python pipeline/scripts/merge.py \
  --base data/raw/coco.json \
  --batch <export-del-companero>.json \
  --out data/raw/coco.json
# el script solo transforma JSON: copiar a mano los .jpg del lote a
# data/raw/images/ antes de este paso (igual que validate.py, tampoco
# toca archivos de imagen)
dvc add data/raw/coco.json data/raw/images
dvc push -r prod
# commit solo de los .dvc — igual que ya está documentado arriba para dev
```

Si el lote entrante trae un `file_name` que ya existe en el base, `merge.py`
falla nombrando el archivo exacto en vez de sobrescribir en silencio —
señal de que dos compañeros nombraron algo igual y hay que coordinarse
antes de fusionar.

**Exporta solo el lote nuevo, no todo el portal.** El botón «COCO» exporta
*todo* lo que hay en la base del portal, incluidos los lotes que ya se
fusionaron; fusionar ese export duplicaría esas imágenes. Filtra por las
imágenes del lote nuevo (o vacía la base del portal entre lotes, una vez que el
lote anterior ya está en `data/raw`).

**Quitar una clase fuera de alcance** (p. ej. `bicycle`, que un lote trajo pero
no es una de las dos clases elegidas): `min_images_per_class` toma el mínimo de
*todas* las clases con datos, así que una clase con pocas imágenes deja la
compuerta en rojo aunque `car` y `person` pasen de 300.

```bash
python pipeline/scripts/drop_category.py   --coco data/raw/coco.json --drop bicycle --out data/raw/coco.json
```

Solo transforma JSON: conserva todas las imágenes, no renumera ids, y un nombre
que no existe falla con un error en vez de no hacer nada. Reporta cuántas
imágenes se quedaron sin ninguna caja.

Specs en `features/specs/f6-02-merge-lotes.feature`, con step definitions
en `tests/step_defs/test_f6_02_merge_lotes.py`.

**Verificado en vivo:** cuenta AWS y bucket `s3://proyecto2-dataset-quality-gate-prod`
creados, coincide con `.dvc/config`. `aws sts get-caller-identity --profile
mlops-p2` y `aws s3 ls s3://proyecto2-dataset-quality-gate-prod --profile
mlops-p2` confirmaron la identidad y el acceso (en ese momento el bucket
estaba vacío). `dvc remote modify --local prod profile mlops-p2` +
`dvc status -r prod` confirmaron que DVC ve el remote correctamente.

**Push real a PROD (verificado):** `dvc push -r prod` se corrió cuatro veces con
datos reales: el primer lote de Ale (105 objetos), el lote de Juan Pablo
fusionado sobre ese (104 objetos, con sus propias llaves del grupo IAM), el lote
de Josué más la reserva (134) y el dataset final (43). El bucket tiene 386
objetos (70.3 MB) y `dvc status -c -r prod` dice *in sync*. Round-trip: en un
clon nuevo con caché vacío, `dvc pull -r prod` trajo las 369 fotos y el md5 de
`data/raw/coco.json` coincidió (`c500a26a…`).

**Dataset final en `main`:** 369 imágenes, 1465 cajas, `car` 317 / `person` 362.
La compuerta (`python -m dataset_pipeline.quality_gate.cli`, `quality.yaml` con
`min_images_per_class` ≥ 300 en severidad `fail`) **pasa** con 317.
