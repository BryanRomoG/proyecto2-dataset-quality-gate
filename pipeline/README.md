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

## Contenido (Frente 2 — T-103)

`src/dataset_pipeline/coco/models.py` define los modelos Pydantic v2 del COCO
(`CocoDataset`, `CocoImage`, `CocoAnnotation`, `CocoCategory`), reflejando
uno a uno los esquemas Zod de `server/src/export/coco.schema.ts`. Un COCO mal
formado se rechaza nombrando el campo (bbox con aridad incorrecta,
`category_id` inexistente, `image_id` huérfano) en vez de un traceback crudo.
