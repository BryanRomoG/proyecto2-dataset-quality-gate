import { z } from 'zod';

// T-104: contratos congelados por Bryan en T-101. La UI los consume tal cual
// via /api/contracts/*; todavía son datos de ejemplo, no telemetría real
// (eso llega en T-204).

export const qualityCheckSchema = z.object({
  name: z.string(),
  value: z.number(),
  threshold: z.number(),
  direction: z.string(),
  severity: z.string(),
  passed: z.boolean(),
  offending_samples: z.array(z.string()),
});

export const qualitySchema = z.object({
  passed: z.boolean(),
  checks: z.array(qualityCheckSchema),
});

export type Quality = z.infer<typeof qualitySchema>;

export const splitsSchema = z.object({
  seed: z.number(),
  ratios: z.object({
    train: z.number(),
    val: z.number(),
    test: z.number(),
  }),
  assignments: z.record(z.string(), z.string()),
  counts: z.object({
    train: z.number(),
    val: z.number(),
    test: z.number(),
  }),
});

export type Splits = z.infer<typeof splitsSchema>;

export const versionDiffSchema = z.object({
  from: z.string(),
  to: z.string(),
  images_added: z.array(z.number()),
  images_removed: z.array(z.number()),
  boxes_added: z.array(z.number()),
  boxes_removed: z.array(z.number()),
  images_per_class: z.record(z.string(), z.number()),
  classes_below_minimum: z.array(z.string()),
});

export const releaseSchema = z.object({
  version: z.string(),
  message: z.string(),
  created_at: z.string(),
  dvc_rev: z.string(),
  diff_vs_previous: versionDiffSchema.nullable(),
});

export const versionsSchema = z.object({
  current: z.string(),
  releases: z.array(releaseSchema),
});

export type Versions = z.infer<typeof versionsSchema>;
export type Release = z.infer<typeof releaseSchema>;

async function getJson<T>(url: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${url} (status ${response.status})`);
  }
  return schema.parse(await response.json());
}

export function fetchQuality(): Promise<Quality> {
  return getJson('/api/contracts/quality', qualitySchema);
}

export function fetchSplits(): Promise<Splits> {
  return getJson('/api/contracts/splits', splitsSchema);
}

export function fetchVersions(): Promise<Versions> {
  return getJson('/api/contracts/versions', versionsSchema);
}
