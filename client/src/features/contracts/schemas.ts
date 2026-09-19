import { z } from 'zod';

// Espejo en Zod de los contratos congelados en T-101
// (`contracts/examples/{quality,splits,versions}.json`). Es la única
// definición de la forma que la UI acepta: si Bryan publica una versión
// nueva del contrato con un campo distinto, la pantalla falla aquí con un
// mensaje claro en vez de renderizar `undefined` a medias.

export const splitNameSchema = z.enum(['train', 'val', 'test']);

export type SplitName = z.infer<typeof splitNameSchema>;

const splitTotalsSchema = z.object({
  train: z.number(),
  val: z.number(),
  test: z.number(),
});

// quality.json --------------------------------------------------------------

export const qualityCheckSchema = z.object({
  name: z.string(),
  value: z.number(),
  threshold: z.number(),
  // "gte" = el valor observado debe ser mayor o igual al umbral; "lte", menor o igual.
  direction: z.enum(['gte', 'lte']),
  severity: z.enum(['fail', 'warn']),
  passed: z.boolean(),
  offending_samples: z.array(z.string()),
});

export type QualityCheck = z.infer<typeof qualityCheckSchema>;

export const qualityReportSchema = z.object({
  passed: z.boolean(),
  checks: z.array(qualityCheckSchema),
});

export type QualityReport = z.infer<typeof qualityReportSchema>;

// splits.json ---------------------------------------------------------------

export const splitsReportSchema = z.object({
  seed: z.number(),
  ratios: splitTotalsSchema,
  // Las llaves son ids de imagen, pero en JSON viajan como string.
  assignments: z.record(z.string(), splitNameSchema),
  counts: splitTotalsSchema,
});

export type SplitsReport = z.infer<typeof splitsReportSchema>;

// versions.json -------------------------------------------------------------

export const releaseDiffSchema = z.object({
  from: z.string(),
  to: z.string(),
  images_added: z.array(z.number()),
  images_removed: z.array(z.number()),
  boxes_added: z.array(z.number()),
  boxes_removed: z.array(z.number()),
  images_per_class: z.record(z.string(), z.number()),
  classes_below_minimum: z.array(z.string()),
});

export type ReleaseDiff = z.infer<typeof releaseDiffSchema>;

export const releaseSchema = z.object({
  version: z.string(),
  message: z.string(),
  created_at: z.string(),
  dvc_rev: z.string(),
  // El primer release no tiene contra qué comparar: el contrato lo marca
  // como null explícito, no como campo ausente.
  diff_vs_previous: releaseDiffSchema.nullable(),
});

export type Release = z.infer<typeof releaseSchema>;

export const versionsReportSchema = z.object({
  current: z.string(),
  releases: z.array(releaseSchema),
});

export type VersionsReport = z.infer<typeof versionsReportSchema>;
