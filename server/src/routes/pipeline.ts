import { type NextFunction, type Request, type Response, Router } from 'express';
import type { z } from 'zod';
import { artifactRelativePath, readPipelineArtifact } from '../lib/pipeline-artifacts';
import { evaluateGate } from '../pipeline/gate';
import { policyPath, rawImagesDir } from '../pipeline/paths';
import { PolicyValidationError, readPolicy, writePolicy } from '../pipeline/policy-store';
import { resolveAnalyzerSamples } from '../pipeline/samples';
import {
  cocoSchema,
  embeddingSchema,
  qualityMetricsSchema,
  splitsArtifactSchema,
  versionsArtifactSchema,
} from '../pipeline/schemas';
import { buildSplitsReport } from '../pipeline/splits-report';

// Pantallas de la sección 7 (Analyzers, Splits, Versions, Settings,
// Explorar y el estado de la compuerta del Overview). Todas leen los
// artefactos que escribe el pipeline en data/processed/ — el server los
// valida y los agrega, pero no recalcula ningún analizador.
export const pipelineRouter = Router();

class ArtifactUnavailableError extends Error {
  constructor(
    public readonly fileName: string,
    public readonly hint: string,
  ) {
    super(`El artefacto ${artifactRelativePath(fileName)} todavía no está materializado.`);
    this.name = 'ArtifactUnavailableError';
  }
}

const DVC_HINT = 'Corre `dvc pull` (o `dvc repro`) para materializar los artefactos del pipeline.';

type Loaded<T> = { data: T; generatedAt: string; path: string };

async function loadArtifact<T>(
  fileName: string,
  schema: z.ZodType<T>,
  hint: string = DVC_HINT,
): Promise<Loaded<T>> {
  const artifact = await readPipelineArtifact(fileName);
  if (artifact === null) {
    throw new ArtifactUnavailableError(fileName, hint);
  }
  const parsed = schema.safeParse(artifact.data);
  if (!parsed.success) {
    // Se nombra el archivo y el campo: un "error interno" genérico mandaría
    // a adivinar qué artefacto cambió de forma.
    const issues = parsed.error.issues
      .slice(0, 5)
      .map((issue) => `${issue.path.join('.') || '(raíz)'}: ${issue.message}`);
    throw new ArtifactShapeError(artifact.path, issues);
  }
  return { data: parsed.data, generatedAt: artifact.generatedAt, path: artifact.path };
}

class ArtifactShapeError extends Error {
  constructor(
    public readonly artifactPath: string,
    public readonly issues: string[],
  ) {
    super(`El artefacto ${artifactPath} no tiene la forma esperada: ${issues.join('; ')}`);
    this.name = 'ArtifactShapeError';
  }
}

pipelineRouter.get('/gate', async (_req, res, next) => {
  try {
    const [policy, metrics] = await Promise.all([
      readPolicy(policyPath()),
      loadArtifact('quality_metrics.json', qualityMetricsSchema),
    ]);
    res.status(200).json({
      ...evaluateGate(policy, metrics.data),
      generatedAt: metrics.generatedAt,
      source: metrics.path,
    });
  } catch (error) {
    next(error);
  }
});

pipelineRouter.get('/analyzers', async (_req, res, next) => {
  try {
    const [metrics, coco] = await Promise.all([
      loadArtifact('quality_metrics.json', qualityMetricsSchema),
      loadArtifact('coco.validated.json', cocoSchema),
    ]);
    res.status(200).json({
      generatedAt: metrics.generatedAt,
      source: metrics.path,
      metrics: metrics.data,
      samples: resolveAnalyzerSamples(coco.data, metrics.data),
    });
  } catch (error) {
    next(error);
  }
});

pipelineRouter.get('/splits', async (_req, res, next) => {
  try {
    const [coco, splits, metrics] = await Promise.all([
      loadArtifact('coco.validated.json', cocoSchema),
      loadArtifact('splits.json', splitsArtifactSchema),
      loadArtifact('quality_metrics.json', qualityMetricsSchema),
    ]);
    res.status(200).json({
      generatedAt: splits.generatedAt,
      source: splits.path,
      report: buildSplitsReport(coco.data, splits.data, metrics.data),
    });
  } catch (error) {
    next(error);
  }
});

pipelineRouter.get('/versions', async (_req, res, next) => {
  try {
    const versions = await loadArtifact(
      'versions.json',
      versionsArtifactSchema,
      'Genera la línea de versiones con `python pipeline/scripts/build_versions.py`.',
    );
    res.status(200).json({
      generatedAt: versions.generatedAt,
      source: versions.path,
      versions: versions.data,
    });
  } catch (error) {
    next(error);
  }
});

pipelineRouter.get('/embedding', async (_req, res, next) => {
  try {
    const embedding = await loadArtifact(
      'embedding.json',
      embeddingSchema,
      'Precalcula la proyección con `python pipeline/scripts/embed.py` (o `dvc repro`).',
    );
    res.status(200).json({
      generatedAt: embedding.generatedAt,
      source: embedding.path,
      embedding: embedding.data,
    });
  } catch (error) {
    next(error);
  }
});

pipelineRouter.get('/settings', async (_req, res, next) => {
  try {
    res.status(200).json({ policy: await readPolicy(policyPath()) });
  } catch (error) {
    next(error);
  }
});

// Escribe quality.yaml y devuelve, de una vez, la compuerta re-evaluada con
// la política nueva: la pantalla muestra el efecto del cambio sin esperar a
// la siguiente corrida de `dvc repro`.
pipelineRouter.put('/settings', async (req, res, next) => {
  try {
    const policy = await writePolicy(policyPath(), req.body);
    const metrics = await readPipelineArtifact('quality_metrics.json');
    const parsed = metrics ? qualityMetricsSchema.safeParse(metrics.data) : null;
    res.status(200).json({
      policy,
      gate: parsed?.success ? evaluateGate(policy, parsed.data) : null,
    });
  } catch (error) {
    next(error);
  }
});

// Las imágenes del dataset viven en data/raw/images (DVC). Solo se sirve un
// nombre de archivo simple: sin separadores ni `..`, para que
// /api/pipeline/images/../../.env no pueda salirse de la carpeta.
const SAFE_IMAGE_NAME = /^[\w][\w.\- ]*\.(?:jpe?g|png|webp)$/i;

pipelineRouter.get('/images/:fileName', (req, res, next) => {
  const { fileName } = req.params;
  if (!SAFE_IMAGE_NAME.test(fileName) || fileName.includes('..')) {
    res.status(400).json({ error: 'Nombre de imagen inválido.' });
    return;
  }
  res.sendFile(fileName, { root: rawImagesDir(), maxAge: '1h' }, (error) => {
    if (!error) return;
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      res.status(404).json({ error: `La imagen ${fileName} no está materializada (dvc pull).` });
      return;
    }
    next(error);
  });
});

pipelineRouter.use((error: unknown, _req: Request, res: Response, next: NextFunction) => {
  if (error instanceof ArtifactUnavailableError) {
    res.status(503).json({
      error: error.message,
      expectedPath: artifactRelativePath(error.fileName),
      hint: error.hint,
    });
    return;
  }
  if (error instanceof ArtifactShapeError) {
    res.status(500).json({ error: error.message, artifact: error.artifactPath });
    return;
  }
  if (error instanceof PolicyValidationError) {
    res.status(422).json({ error: error.message, issues: error.issues });
    return;
  }
  if (error instanceof SyntaxError) {
    res.status(500).json({ error: `Un artefacto no es JSON válido: ${error.message}` });
    return;
  }
  next(error);
});
