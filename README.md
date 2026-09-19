# Portal de Anotación de Imágenes

Portal web para anotar imágenes con bounding boxes, gestionar categorías, revisar métricas en un dashboard y exportar el dataset en formato COCO.

## Stack

- Frontend: React + TypeScript + Vite
- Backend: Express + TypeScript (sirve el build de Vite — un solo proceso, un solo puerto)
- Validación: Zod 4
- ORM: Drizzle · Base de datos: MariaDB · Imágenes: MinIO
- Anotador: Konva + react-konva · Dashboard: Recharts
- Testing: Vitest + React Testing Library · BDD: Cucumber.js
- Calidad: Biome · Entorno: Docker Compose

## Estado actual

Proyecto completo y funcional: portal de anotación de imágenes con persistencia real,
dashboard de métricas, búsqueda con filtros y exportación a formato COCO.

- **Monolito real, un solo puerto**: Express sirve el build de Vite en producción; en desarrollo corre Vite en modo middleware dentro del mismo proceso Express (con HMR). No hay dos servidores ni dos puertos que coordinar — `npm run dev` levanta todo.
- **Config por entorno con Zod**: `server/src/config/env.ts` valida `process.env` (cargado desde `.env` con `dotenv`) al arrancar. Si falta o está mal una variable, el server falla rápido con un mensaje claro en vez de fallar más adelante de forma confusa.
- **`.env.example`** versionado con placeholders (sin secretos reales) para MariaDB y MinIO. `.env` real está en `.gitignore`.
- **Docker Compose** con tres servicios (`app`, `mariadb`, `minio`), healthchecks, y todas las credenciales/puertos/buckets leídos de `.env` — nada hardcodeado.
- **TypeScript estricto**: `tsconfig.base.json` (compartido) + `tsconfig.client.json` / `tsconfig.server.json`, con `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`. `npm run typecheck` pasa sin errores.
- **Biome** configurado (`biome.json`) prohibiendo `any` explícito y `console.log`, con `npm run check` en 0 errores / 0 warnings.
- **Separación UI / Lógica / Datos**: la UI (`client/`) nunca importa nada de `server/src/db` ni del cliente de MinIO. Todo pasa por `/api/*` (`server/src/routes/`).
- **Persistencia**: esquema Drizzle (imágenes, anotaciones, categorías) con FKs, índices y tipos correctos; migraciones versionadas que se aplican desde cero sin pasos manuales; seeder idempotente con categorías e imágenes de ejemplo (subidas de verdad a MinIO).
- **Portal de anotación**: subida de imágenes con validación de tipo/tamaño y feedback; editor de bounding boxes (Konva) con crear/mover/redimensionar/borrar y persistencia al recargar; categorías con color y validación de clase obligatoria; zoom, deshacer, navegación entre imágenes y "guardar y siguiente".
- **Dashboard**: métricas calculadas desde la BD (nunca hardcodeadas) y gráficas por categoría/progreso (Recharts).
- **Telemetría real del pipeline en el dashboard (T-204)**: el dashboard consume la salida real de los 5 analizadores del Frente 3 (T-202) desde `GET /api/dashboard/quality-metrics`, que sirve el artefacto que DVC materializa en `data/processed/quality_metrics.json` (objetos pequeños, desbalance de clases, cajas inválidas, sesgo espacial con percentiles y duplicados por pHash). La pantalla **se actualiza sola cada 5 s sin recargar** (refetch periódico, en pausa mientras la pestaña está oculta y con refresco inmediato al volver a ella); si un refresco falla se conserva la última lectura buena con un aviso, y si el artefacto todavía no está materializado el dashboard dice qué falta (`dvc pull` / `dvc repro`) en vez de mostrar ceros como si fueran datos reales.
- **Búsqueda**: operadores tipo `car AND person` resueltos en SQL (no en memoria), filtros combinables por clase/estado/rango de fechas, con paginación correcta.
- **Aplicación de calidad de datasets (sección 7)**: además del Overview, cinco pantallas leen los artefactos reales de `data/processed/` a través de `/api/pipeline/*` (nunca datos de ejemplo; si falta un artefacto la pantalla dice qué comando lo genera). **Overview** suma el estado de la compuerta (`quality.yaml` evaluado contra la telemetría) y los checks fallidos. **Analyzers**: las 5 pestañas con gráfica y muestras ofensoras navegables (imagen + caja). **Splits**: distribución de clases por split, proporción real vs objetivo y chequeo de fuga (pares de pHash repartidos entre splits). **Versions**: línea de tiempo de releases, estado DEV/PROD y comparación entre dos versiones cualesquiera. **Settings**: edita umbral y severidad en `quality.yaml` (se escribe el archivo, conservando sus comentarios) y muestra cómo queda la compuerta con la política nueva. **Explorar**: proyección PCA 2D precomputada offline (etapa `embed` de `dvc.yaml`) con hover que muestra la imagen y filtro por clase en el cliente. `versions.json` no es una etapa de DVC (depende de los tags de git y de acceso a los remotes): se genera con `python pipeline/scripts/build_versions.py --out data/processed/versions.json` y hay que regenerarlo al publicar un release. Para las miniaturas, `RAW_IMAGES_DIR` (default `data/raw/images`) debe estar materializado con `dvc pull`.
- **Contratos del dataset (T-104)**: sexta pantalla ("Contratos") que renderiza completos los tres contratos congelados en T-101 — `quality.json` (compuerta: valor vs umbral, dirección, severidad y muestras ofensoras por check), `splits.json` (seed, ratios, counts y la asignación imagen → split) y `versions.json` (versión actual e historial de releases con su diff: imágenes/cajas agregadas y eliminadas, imágenes por clase y clases bajo el mínimo). Se sirven tal cual desde `GET /api/contracts/{quality,splits,versions}` y se validan con Zod en el cliente. Esta pantalla muestra a propósito los contratos **congelados** (la forma acordada del dato, no el dato vivo); la salida real del pipeline se ve en el Dashboard (T-204).
=======
- **Exportación COCO**: JSON válido con `images`/`annotations`/`categories`, ids consistentes, `bbox` en píxeles absolutos, `area` coherente, `iscrowd` presente, descarga completa del dataset desde la UI.
- **Vitest** (unit/integración) y **Cucumber.js** (Gherkin, con trazabilidad SPEC → `.feature` → step definitions) cubriendo las reglas críticas de negocio, incluidas anotación y exportación COCO.

Verificado end-to-end: `npm install`, `npm run typecheck`, `npm run check`, `npm test`, `npm run test:bdd`, `docker compose up mariadb minio -d` + `npm run db:migrate` + `npm run db:seed` + `npm run dev` sirviendo la app en `:3000`, y `docker compose up --build` sirviendo el monolito completo en `:3100`.

## Cómo correrlo

### Requisitos

- Node.js 22+
- Docker y Docker Compose

### Clonar

```bash
git clone https://github.com/BryanRomoG/proyecto2-dataset-quality-gate.git
cd proyecto2-dataset-quality-gate
```

### Setup inicial

```bash
cp .env.example .env
npm install
```
```windows cmd
copy .env.example .env
npm install
```

### Desarrollo (hot reload, puerto 3000)

Levanta solo la infraestructura (MariaDB + MinIO) con Docker, y el proceso Node de la app en local:

```bash
docker compose up mariadb minio -d
npm run db:migrate
npm run db:seed
npm run dev
```

App disponible en `http://localhost:3000`. Health check: `http://localhost:3000/api/health`.

Para parar: `Ctrl+C` en la terminal de `npm run dev`, y `docker compose down`.

### Producción / monolito completo (puerto 3100)

```bash/Windows cmd
docker compose up --build
```

Levanta app + MariaDB + MinIO con un solo comando. La app sirve el build de React y la API desde el mismo proceso/puerto. El puerto de este servicio está fijo en `3100` dentro de `docker-compose.yml` (no depende de `PORT` en tu `.env`, que sigue siendo `3000` para el modo on-premise) — no hace falta editar nada a mano entre un modo y otro.

### Scripts

| Script | Qué hace |
|---|---|
| `npm run dev` | Servidor Express + Vite en modo middleware (HMR), puerto `PORT` (default 3000) |
| `npm run build` | Build de producción del cliente (`client/dist`) |
| `npm start` | Arranca el servidor en modo producción (sirve `client/dist`) |
| `npm run typecheck` | `tsc --noEmit` sobre cliente y servidor (TypeScript estricto) |
| `npm test` | Pruebas unitarias/componentes (Vitest) |
| `npm run test:bdd` | Escenarios Gherkin (Cucumber.js) |
| `npm run check` | Lint + format check (Biome) |
| `npm run check:fix` | Autofix de Biome |

## Estructura

```
client/            React + Vite (UI)
server/src/
  index.ts         Entry point: Express + integración Vite
  config/env.ts     Config validada con Zod (.env)
  routes/           Routers de la API (/api/*)
  lib/minio.ts       Cliente MinIO
  db/               Esquema Drizzle, migraciones, seeder (ver server/src/db/README.md)
contracts/examples/ Contratos congelados (T-101) que consume la pantalla "Contratos"
data/processed/     Artefactos reales del pipeline (DVC): telemetría que lee el dashboard
=======
features/           SPECs en Gherkin + step definitions (ver features/README.md)
```

La UI nunca accede a MariaDB ni a MinIO directamente: todo pasa por `/api/*` en el servidor Express.

## Pendiente (fuera del alcance de la rúbrica)

- Añadir typecheck al CI (lint + tests de Python ya corren en `pipeline-ci.yml`; el portal tiene `ci.yml`).
- Decidir si se agrega autenticación (no está en la rúbrica como requisito explícito).
