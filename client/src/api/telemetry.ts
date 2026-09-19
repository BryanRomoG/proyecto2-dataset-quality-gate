import { z } from 'zod';

// Telemetría real del pipeline (T-204): espejo en Zod de los 5 reportes
// Pydantic del Frente 3 (T-202), tal como los escribe
// `pipeline/scripts/analyze.py` en `data/processed/quality_metrics.json`.
// Si un analizador cambia su reporte, la validación truena aquí nombrando
// el campo, en vez de renderizar huecos en el dashboard.

const smallObjectsSchema = z.object({
  threshold_px: z.number(),
  total_annotations: z.number(),
  small_count: z.number(),
  percentage_below_threshold: z.number(),
  // null cuando ningún objeto cae bajo el umbral: no hay "clase más afectada".
  most_affected_category: z.string().nullable(),
  offending_sample_ids: z.array(z.number()),
});

const classImbalanceSchema = z.object({
  counts: z.record(z.string(), z.number()),
  // null cuando alguna clase tiene 0 imágenes (el ratio sería división entre cero).
  majority_minority_ratio: z.number().nullable(),
  classes_below_minimum: z.array(z.string()),
});

const invalidBoxesSchema = z.object({
  total_annotations: z.number(),
  invalid: z.array(
    z.object({
      annotation_id: z.number(),
      reasons: z.array(z.string()),
    }),
  ),
});

const spatialBiasSchema = z.object({
  count: z.number(),
  mean: z.number(),
  median: z.number(),
  p10: z.number(),
  p25: z.number(),
  p75: z.number(),
  p90: z.number(),
});

const duplicatesSchema = z.object({
  distance_threshold: z.number(),
  pairs: z.array(
    z.object({
      image_id_a: z.number(),
      image_id_b: z.number(),
      hash_distance: z.number(),
      similarity: z.number(),
    }),
  ),
});

export const qualityMetricsSchema = z.object({
  small_objects: smallObjectsSchema,
  class_imbalance: classImbalanceSchema,
  invalid_boxes: invalidBoxesSchema,
  spatial_bias: spatialBiasSchema,
  duplicates: duplicatesSchema,
});

export type QualityMetrics = z.infer<typeof qualityMetricsSchema>;

const telemetrySchema = z.object({
  /** mtime del artefacto: cuándo lo escribió el pipeline. */
  generatedAt: z.string(),
  source: z.string(),
  metrics: qualityMetricsSchema,
});

const unavailableSchema = z.object({
  error: z.string(),
  expectedPath: z.string(),
  hint: z.string(),
});

export type QualityMetricsResult =
  | { available: true; generatedAt: string; source: string; metrics: QualityMetrics }
  | { available: false; message: string; expectedPath: string; hint: string };

export async function fetchQualityMetrics(): Promise<QualityMetricsResult> {
  const response = await fetch('/api/dashboard/quality-metrics');

  // 503 = el pipeline todavía no dejó el artefacto en disco. Es un estado
  // esperado (clon limpio sin `dvc pull`), no una falla: se devuelve como
  // dato para que el dashboard lo explique, no como excepción.
  if (response.status === 503) {
    const body = unavailableSchema.parse(await response.json());
    return {
      available: false,
      message: body.error,
      expectedPath: body.expectedPath,
      hint: body.hint,
    };
  }

  if (!response.ok) {
    throw new Error(`No se pudo cargar la telemetría del pipeline (status ${response.status})`);
  }

  const body = telemetrySchema.parse(await response.json());
  return { available: true, ...body };
}
