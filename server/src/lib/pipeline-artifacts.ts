import { readFile, stat } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { env } from '../config/env';

// Los artefactos del pipeline de Python (T-202 en adelante) no viven en la
// BD ni en el repo: DVC los materializa en disco (`data/processed/`). El
// server los lee de ahí y los expone por /api/*; la UI nunca toca el disco.

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, '../../..');

export type PipelineArtifact = {
  /** Ruta relativa al repo, para poder decirle al usuario qué archivo se leyó. */
  path: string;
  /** mtime del archivo: cuándo lo escribió el pipeline, no cuándo lo leímos. */
  generatedAt: string;
  data: unknown;
};

export function artifactsDir(): string {
  return path.isAbsolute(env.PIPELINE_ARTIFACTS_DIR)
    ? env.PIPELINE_ARTIFACTS_DIR
    : path.resolve(repoRoot, env.PIPELINE_ARTIFACTS_DIR);
}

/** Ruta relativa al repo del artefacto, para mensajes de error accionables. */
export function artifactRelativePath(fileName: string): string {
  return path.relative(repoRoot, path.join(artifactsDir(), fileName)).split(path.sep).join('/');
}

/**
 * Devuelve `null` cuando el artefacto todavía no está materializado (clon
 * limpio sin `dvc pull`/`dvc repro`). Eso **no** es un error: es un estado
 * normal que la UI tiene que poder mostrar tal cual, en vez de inventar
 * números o quedarse cargando para siempre.
 */
export async function readPipelineArtifact(
  fileName: string,
  directory: string = artifactsDir(),
): Promise<PipelineArtifact | null> {
  const filePath = path.join(directory, fileName);

  let stats: Awaited<ReturnType<typeof stat>>;
  try {
    stats = await stat(filePath);
  } catch {
    return null;
  }

  const raw = await readFile(filePath, 'utf-8');
  return {
    path: path.relative(repoRoot, filePath).split(path.sep).join('/'),
    generatedAt: stats.mtime.toISOString(),
    data: JSON.parse(raw),
  };
}
