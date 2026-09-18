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

> Nota: este archivo se está construyendo en paralelo en dos ramas distintas
> (`feat/frente4-quality-gate` y esta, `fix/t403-ruff-ci-higiene`) — cuando
> ambas se mergeen a `main` va a haber un conflicto trivial de merge en esta
> tabla (dos secciones agregadas al mismo archivo). Se resuelve combinando
> ambas listas de filas, no descartando ninguna.

| SPEC ID | Regla de negocio | Frente | Archivo `.feature` | Dueño |
|---|---|---|---|---|
| SPEC-F10-04 | El workflow de CI corre Ruff (lint + format) y pytest en cada push/PR a `main`, sin `continue-on-error` en ningún paso — un fallo real tumba el build | 10 — Ruff, pytest y CI | `f10-04-ci.feature` | Juan Pablo |
| SPEC-F11-03 | `.gitignore` cubre `.env`, `__pycache__`, `.venv`, `.dvc/cache`, `*.tfstate` y `node_modules` — ninguno aparece en `git ls-files` | 11 — Git y flujo de trabajo | `f10-04-ci.feature` | Juan Pablo |

## Notas de Frente 10/11 (issue #19, T-4.3)

- **Workflow separado del de Node**: `.github/workflows/pipeline-ci.yml`
  (Python: `pip install -e ".[dev]"`, `ruff check .`, `ruff format --check .`,
  `pytest`) vive aparte de `ci.yml` (Node/Josue, T-403). Un solo archivo
  mezclando ambos stacks sería más frágil — cualquier cambio a uno arriesga
  romper la sintaxis del otro, y un fallo de npm no debería impedir ver si
  Ruff/pytest también fallaron, o viceversa.
- **"Corre el workflow de GitHub Actions" en el escenario Gherkin no
  ejecuta el YAML real** (no hay `act` disponible en este entorno de
  desarrollo) — reproduce cada paso del workflow (`ruff check`, `pytest`)
  como subproceso real contra código deliberadamente roto, y confirma exit
  code ≠ 0. Es la misma técnica de T-4.2 (mutation testing), aplicada aquí
  al workflow en sí.
- **`ruff format .` se corrió sobre todo `pipeline/`** (no solo los
  archivos de este ticket): el AC de este issue exige `ruff format
  --check .` en cero para *todo* el repo, así que a diferencia de Frente 4
  (donde reformatear el código de Ale hubiera sido ruido fuera de alcance),
  aquí sí es el propósito explícito del ticket. Eran 6 archivos con drift
  de formato, 5 preexistentes de Ale + 1 propio.
- **Bug real encontrado escribiendo el step `.gitignore correcto`**: un
  matching por substring ingenuo marcaba `.env.example` (que SÍ debe
  versionarse) como si fuera un `.env` real, solo por contener "env" como
  substring. Corregido con matching preciso por patrón
  (`_matches_forbidden_pattern` en `test_f10_04_ci.py`), no una
  coincidencia de texto libre.
- **Auditoría de `git ls-files` (DoD del issue)**: sin `.env`,
  `__pycache__`, `.venv`, `.dvc/cache`, `.tfstate` ni `node_modules`
  versionados. Sí aparecen 3 archivos `.jpg` bajo
  `server/src/db/seed-assets/` — **no son "imagen suelta" del dataset de
  anotación** (la preocupación real del AC, que las ~300+ imágenes del
  Proyecto 2 nunca bypaseen DVC): son las 3 imágenes de ejemplo del
  seeder del portal Node, del Proyecto 1, ya entregado y evaluado. Se
  documentan aquí en vez de borrarlas sin consultar al equipo — están
  fuera del alcance de este ticket.
- Revisado también `git log --all -p -S 'AKIA'` (llaves AWS) y archivos
  `.env`/`.tfstate` creados alguna vez en el historial completo, no solo
  en `HEAD` (M2 del plan de trabajo: "no basta con limpiar HEAD, se revisa
  el historial completo") — limpio, sin resultados.
