import { count, eq, inArray } from 'drizzle-orm';
import { Router } from 'express';
import { db } from '../db/client';
import { annotations, categories, images } from '../db/schema';
import { artifactRelativePath, readPipelineArtifact } from '../lib/pipeline-artifacts';

export const dashboardRouter = Router();

// Estados que cuentan como "ya anotada" para el progreso del dashboard:
// 'reviewed' implica que ya pasó por 'annotated' en su momento.
const ANNOTATED_STATUSES = ['annotated', 'reviewed'] as const;

dashboardRouter.get('/summary', async (_req, res, next) => {
  try {
    const [totalImagesRow] = await db.select({ value: count() }).from(images);
    const [annotatedImagesRow] = await db
      .select({ value: count() })
      .from(images)
      .where(inArray(images.status, [...ANNOTATED_STATUSES]));
    const [totalBoundingBoxesRow] = await db.select({ value: count() }).from(annotations);
    const [totalCategoriesRow] = await db.select({ value: count() }).from(categories);

    res.status(200).json({
      totalImages: totalImagesRow?.value ?? 0,
      annotatedImages: annotatedImagesRow?.value ?? 0,
      totalBoundingBoxes: totalBoundingBoxesRow?.value ?? 0,
      totalCategories: totalCategoriesRow?.value ?? 0,
    });
  } catch (error) {
    next(error);
  }
});

dashboardRouter.get('/objects-by-category', async (_req, res, next) => {
  try {
    // LEFT JOIN a propósito: una categoría sin anotaciones todavía debe
    // aparecer en la gráfica con 0, no desaparecer del resultado.
    const rows = await db
      .select({
        categoryId: categories.id,
        categoryName: categories.name,
        color: categories.color,
        objectCount: count(annotations.id),
      })
      .from(categories)
      .leftJoin(annotations, eq(annotations.categoryId, categories.id))
      .groupBy(categories.id, categories.name, categories.color)
      .orderBy(categories.name);

    res.status(200).json({ objectsByCategory: rows });
  } catch (error) {
    next(error);
  }
});

// T-204: telemetría real de los 5 analizadores del Frente 3 (T-202). El
// dashboard deja de leer los JSON de ejemplo y consume este endpoint, que
// sirve el artefacto que el pipeline escribió de verdad — sin recalcular
// nada aquí: el server no reimplementa los analizadores, solo los expone.
const QUALITY_METRICS_FILE = 'quality_metrics.json';

dashboardRouter.get('/quality-metrics', async (_req, res, next) => {
  try {
    const artifact = await readPipelineArtifact(QUALITY_METRICS_FILE);

    // Todavía sin `dvc pull`/`dvc repro`: no es un error del server ni de
    // la UI. Se responde 503 con la ruta esperada y el comando que falta,
    // para que el dashboard pueda decirlo en pantalla en vez de mostrar
    // métricas vacías que parecerían datos reales.
    if (artifact === null) {
      res.status(503).json({
        error: 'La telemetría del pipeline todavía no está materializada en disco.',
        expectedPath: artifactRelativePath(QUALITY_METRICS_FILE),
        hint: 'Corre `dvc pull` (o `dvc repro`) para materializar los artefactos del pipeline.',
      });
      return;
    }

    res.status(200).json({
      generatedAt: artifact.generatedAt,
      source: artifact.path,
      metrics: artifact.data,
    });
  } catch (error) {
    // Un artefacto corrupto se reporta nombrando el archivo: el handler
    // genérico diría solo "Error interno del servidor" y mandaría a
    // adivinar dónde está el problema.
    if (error instanceof SyntaxError) {
      res.status(500).json({
        error: `El artefacto ${artifactRelativePath(QUALITY_METRICS_FILE)} no es JSON válido: ${error.message}`,
      });
      return;
    }
    next(error);
  }
});
