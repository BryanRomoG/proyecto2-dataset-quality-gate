import { z } from 'zod';
import { qualityMetricsSchema } from './telemetry';

// Cliente de /api/pipeline/*: las pantallas Analyzers, Splits, Versions,
// Settings y Explorar (sección 7). Igual que el resto de la app, la UI nunca
// toca el disco ni el pipeline: todo pasa por la API, y cada respuesta se
// valida con Zod para que un cambio de forma falle nombrando el campo.

export type Artifact<T> =
  | { available: true; data: T }
  | { available: false; message: string; expectedPath: string; hint: string };

const unavailableSchema = z.object({
  error: z.string(),
  expectedPath: z.string(),
  hint: z.string(),
});

async function errorMessage(response: Response, url: string): Promise<string> {
  try {
    const body = await response.json();
    if (typeof body?.error === 'string') return body.error;
  } catch {
    // cuerpo no-JSON: se cae al mensaje genérico
  }
  return `No se pudo cargar ${url} (status ${response.status})`;
}

// 503 = el pipeline todavía no dejó el artefacto (clon limpio sin `dvc pull`).
// Es un estado esperado, no una falla: se devuelve como dato para que la
// pantalla explique qué falta en vez de mostrar ceros que parecerían reales.
async function getArtifact<T>(url: string, schema: z.ZodType<T>): Promise<Artifact<T>> {
  const response = await fetch(url);
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
    throw new Error(await errorMessage(response, url));
  }
  return { available: true, data: schema.parse(await response.json()) };
}

// --- Compuerta --------------------------------------------------------------

const gateCheckSchema = z.object({
  name: z.string(),
  value: z.number().nullable(),
  threshold: z.number(),
  direction: z.enum(['gte', 'lte']).nullable(),
  severity: z.enum(['warn', 'fail']),
  passed: z.boolean(),
  evaluated: z.boolean(),
  offendingSamples: z.array(z.string()),
});
export type GateCheck = z.infer<typeof gateCheckSchema>;

export const gateSchema = z.object({
  passed: z.boolean(),
  checks: z.array(gateCheckSchema),
  failedChecks: z.number(),
  warnings: z.number(),
  generatedAt: z.string().optional(),
  source: z.string().optional(),
});
export type Gate = z.infer<typeof gateSchema>;

export function fetchGate(): Promise<Artifact<Gate>> {
  return getArtifact('/api/pipeline/gate', gateSchema);
}

// --- Analyzers --------------------------------------------------------------

const imageRefShape = {
  imageId: z.number(),
  fileName: z.string(),
  width: z.number(),
  height: z.number(),
};

const annotationSampleSchema = z.object({
  ...imageRefShape,
  annotationId: z.number(),
  category: z.string(),
  bbox: z.tuple([z.number(), z.number(), z.number(), z.number()]),
  reasons: z.array(z.string()),
});
export type AnnotationSample = z.infer<typeof annotationSampleSchema>;

const duplicateSampleSchema = z.object({
  hashDistance: z.number(),
  similarity: z.number(),
  a: z.object(imageRefShape),
  b: z.object(imageRefShape),
});
export type DuplicateSample = z.infer<typeof duplicateSampleSchema>;

const analyzersSchema = z.object({
  generatedAt: z.string(),
  source: z.string(),
  metrics: qualityMetricsSchema,
  samples: z.object({
    small: z.array(annotationSampleSchema),
    invalid: z.array(annotationSampleSchema),
    duplicates: z.array(duplicateSampleSchema),
  }),
});
export type AnalyzersData = z.infer<typeof analyzersSchema>;

export function fetchAnalyzers(): Promise<Artifact<AnalyzersData>> {
  return getArtifact('/api/pipeline/analyzers', analyzersSchema);
}

export function imageUrl(fileName: string): string {
  return `/api/pipeline/images/${encodeURIComponent(fileName)}`;
}

// --- Splits -----------------------------------------------------------------

const splitKey = z.enum(['train', 'val', 'test']);
export type SplitKey = z.infer<typeof splitKey>;

const splitsSchema = z.object({
  generatedAt: z.string(),
  source: z.string(),
  report: z.object({
    seed: z.number(),
    ratios: z.record(z.string(), z.number()),
    imagesPerSplit: z.record(splitKey, z.number()),
    actualRatios: z.record(splitKey, z.number()),
    classes: z.array(
      z.object({
        className: z.string(),
        train: z.number(),
        val: z.number(),
        test: z.number(),
        total: z.number(),
      }),
    ),
    leakage: z.object({
      ok: z.boolean(),
      duplicatePairsChecked: z.number(),
      crossSplitPairs: z.array(
        z.object({
          imageIdA: z.number(),
          imageIdB: z.number(),
          splitA: splitKey,
          splitB: splitKey,
          hashDistance: z.number(),
        }),
      ),
      unassignedImages: z.array(z.number()),
      unknownImages: z.array(z.number()),
      countsConsistent: z.boolean(),
    }),
  }),
});
export type SplitsData = z.infer<typeof splitsSchema>;

export function fetchSplits(): Promise<Artifact<SplitsData>> {
  return getArtifact('/api/pipeline/splits', splitsSchema);
}

// --- Versions ---------------------------------------------------------------

const remoteStatus = z.enum(['in_sync', 'missing', 'unknown']);
export type RemoteStatus = z.infer<typeof remoteStatus>;

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
export type Snapshot = z.infer<typeof snapshotSchema>;

const releaseSchema = z.object({
  version: z.string(),
  message: z.string(),
  created_at: z.string(),
  commit: z.string(),
  dataset_md5: z.string().nullable(),
  snapshot: snapshotSchema.nullable(),
  remotes: z.object({ dev: remoteStatus, prod: remoteStatus }),
  diff_vs_previous: releaseDiffSchema.nullable(),
});
export type Release = z.infer<typeof releaseSchema>;

const versionsSchema = z.object({
  generatedAt: z.string(),
  source: z.string(),
  versions: z.object({ current: z.string().nullable(), releases: z.array(releaseSchema) }),
});
export type VersionsData = z.infer<typeof versionsSchema>;

export function fetchVersions(): Promise<Artifact<VersionsData>> {
  return getArtifact('/api/pipeline/versions', versionsSchema);
}

// --- Explorar (analítica exploratoria) --------------------------------------

const embeddingSchema = z.object({
  generatedAt: z.string(),
  source: z.string(),
  embedding: z.object({
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
  }),
});
export type EmbeddingData = z.infer<typeof embeddingSchema>;
export type EmbeddingPoint = EmbeddingData['embedding']['points'][number];

export function fetchEmbedding(): Promise<Artifact<EmbeddingData>> {
  return getArtifact('/api/pipeline/embedding', embeddingSchema);
}

// --- Settings ---------------------------------------------------------------

export const policySchema = z.object({
  checks: z.record(
    z.string(),
    z.object({ threshold: z.number(), severity: z.enum(['warn', 'fail']) }),
  ),
});
export type Policy = z.infer<typeof policySchema>;

export function fetchSettings(): Promise<Artifact<{ policy: Policy }>> {
  return getArtifact('/api/pipeline/settings', z.object({ policy: policySchema }));
}

export type SaveSettingsResult = { policy: Policy; gate: Gate | null };

export class SettingsValidationError extends Error {
  constructor(public readonly issues: string[]) {
    super(issues.join('; '));
    this.name = 'SettingsValidationError';
  }
}

export async function saveSettings(policy: Policy): Promise<SaveSettingsResult> {
  const response = await fetch('/api/pipeline/settings', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(policy),
  });
  if (response.status === 422) {
    const body = z
      .object({ error: z.string(), issues: z.array(z.string()).optional() })
      .parse(await response.json());
    throw new SettingsValidationError(body.issues ?? [body.error]);
  }
  if (!response.ok) {
    throw new Error(await errorMessage(response, '/api/pipeline/settings'));
  }
  return z
    .object({ policy: policySchema, gate: gateSchema.nullable() })
    .parse(await response.json());
}
