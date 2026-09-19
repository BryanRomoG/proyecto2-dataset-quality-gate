import { z } from 'zod';

// Forma de los artefactos que deja el pipeline de Python en data/processed/.
// Se validan aquí (no se confía en el JSON del disco): un artefacto con otra
// forma truena nombrando el campo en vez de renderizar huecos en la UI.

export const cocoSchema = z.object({
  images: z.array(
    z.object({
      id: z.number(),
      file_name: z.string(),
      width: z.number(),
      height: z.number(),
    }),
  ),
  annotations: z.array(
    z.object({
      id: z.number(),
      image_id: z.number(),
      category_id: z.number(),
      bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]),
    }),
  ),
  categories: z.array(z.object({ id: z.number(), name: z.string() })),
});
export type Coco = z.infer<typeof cocoSchema>;

export const qualityMetricsSchema = z.object({
  small_objects: z.object({
    threshold_px: z.number(),
    total_annotations: z.number(),
    small_count: z.number(),
    percentage_below_threshold: z.number(),
    most_affected_category: z.string().nullable(),
    offending_sample_ids: z.array(z.number()),
  }),
  class_imbalance: z.object({
    counts: z.record(z.string(), z.number()),
    majority_minority_ratio: z.number().nullable(),
    classes_below_minimum: z.array(z.string()),
  }),
  invalid_boxes: z.object({
    total_annotations: z.number(),
    invalid: z.array(z.object({ annotation_id: z.number(), reasons: z.array(z.string()) })),
  }),
  spatial_bias: z.object({
    count: z.number(),
    mean: z.number(),
    median: z.number(),
    p10: z.number(),
    p25: z.number(),
    p75: z.number(),
    p90: z.number(),
  }),
  duplicates: z.object({
    distance_threshold: z.number(),
    pairs: z.array(
      z.object({
        image_id_a: z.number(),
        image_id_b: z.number(),
        hash_distance: z.number(),
        similarity: z.number(),
      }),
    ),
  }),
});
export type QualityMetrics = z.infer<typeof qualityMetricsSchema>;

export const splitNameSchema = z.enum(['train', 'val', 'test']);
export type SplitName = z.infer<typeof splitNameSchema>;

export const splitsArtifactSchema = z.object({
  seed: z.number(),
  ratios: z.record(z.string(), z.number()),
  // Las llaves son ids de imagen; en JSON viajan como string.
  assignments: z.record(z.string(), splitNameSchema),
  counts: z.record(z.string(), z.number()),
});
export type SplitsArtifact = z.infer<typeof splitsArtifactSchema>;

// Espejo de dataset_pipeline.config.quality.QualityPolicy: mismos campos, y
// `extra="forbid"` se traduce en `.strict()`.
export const severitySchema = z.enum(['warn', 'fail']);

export const qualityPolicySchema = z
  .object({
    checks: z.record(
      z.string(),
      z.object({ threshold: z.number().finite().nonnegative(), severity: severitySchema }).strict(),
    ),
  })
  .strict()
  .refine((policy) => 'min_images_per_class' in policy.checks, {
    message: "quality.yaml debe definir el check 'min_images_per_class' (compuerta M3)",
  });
export type QualityPolicy = z.infer<typeof qualityPolicySchema>;

// Salida de pipeline/scripts/embed.py (analítica exploratoria).
export const embeddingSchema = z.object({
  method: z.string(),
  explained_variance: z.array(z.number()).optional(),
  points: z.array(
    z.object({
      image_id: z.number(),
      file_name: z.string(),
      x: z.number(),
      y: z.number(),
      categories: z.array(z.string()),
      split: z.string().nullable().optional(),
    }),
  ),
});
export type Embedding = z.infer<typeof embeddingSchema>;

// Salida de pipeline/scripts/build_versions.py.
const releaseDiffSchema = z.object({
  from: z.string(),
  to: z.string(),
  images_added: z.number(),
  images_removed: z.number(),
  boxes_added: z.number(),
  boxes_removed: z.number(),
  images_per_class: z.record(z.string(), z.number()),
  classes_below_minimum: z.array(z.string()),
  classes_left_minimum: z.array(z.string()),
  small_objects_pct_before: z.number().nullable(),
  small_objects_pct_after: z.number().nullable(),
});
export type ReleaseDiff = z.infer<typeof releaseDiffSchema>;

const snapshotSchema = z.object({
  images: z.number(),
  boxes: z.number(),
  images_per_class: z.record(z.string(), z.number()),
  classes_below_minimum: z.array(z.string()),
  small_objects_pct: z.number(),
});

const remoteStatusSchema = z.enum(['in_sync', 'missing', 'unknown']);

export const versionsArtifactSchema = z.object({
  current: z.string().nullable(),
  releases: z.array(
    z.object({
      version: z.string(),
      message: z.string(),
      created_at: z.string(),
      commit: z.string(),
      dataset_md5: z.string().nullable(),
      snapshot: snapshotSchema.nullable(),
      remotes: z.object({ dev: remoteStatusSchema, prod: remoteStatusSchema }),
      diff_vs_previous: releaseDiffSchema.nullable(),
    }),
  ),
});
export type VersionsArtifact = z.infer<typeof versionsArtifactSchema>;
