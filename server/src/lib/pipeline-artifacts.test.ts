import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { readPipelineArtifact } from './pipeline-artifacts';

// T-204: el dashboard lee telemetría real del pipeline desde disco. Estas
// pruebas fijan el contrato del lector: qué pasa cuando el artefacto está,
// cuando no está todavía, y cuando está corrupto.

let directory: string;

beforeEach(async () => {
  directory = await mkdtemp(path.join(tmpdir(), 'pipeline-artifacts-'));
});

afterEach(async () => {
  await rm(directory, { recursive: true, force: true });
});

describe('readPipelineArtifact', () => {
  it('devuelve el contenido del artefacto y cuándo lo escribió el pipeline', async () => {
    const metrics = { small_objects: { small_count: 3 } };
    await writeFile(path.join(directory, 'quality_metrics.json'), JSON.stringify(metrics), 'utf-8');

    const artifact = await readPipelineArtifact('quality_metrics.json', directory);

    expect(artifact).not.toBeNull();
    expect(artifact?.data).toEqual(metrics);
    expect(artifact?.path).toMatch(/quality_metrics\.json$/);
    // generatedAt sale del mtime del archivo, no de "ahora": es cuándo lo
    // generó el pipeline, no cuándo lo leyó el server.
    expect(Number.isNaN(Date.parse(artifact?.generatedAt ?? ''))).toBe(false);
  });

  it('devuelve null (no lanza) si el pipeline todavía no materializó el artefacto', async () => {
    await expect(readPipelineArtifact('quality_metrics.json', directory)).resolves.toBeNull();
  });

  it('devuelve null si ni siquiera existe la carpeta de artefactos', async () => {
    const missingDir = path.join(directory, 'no-existe');

    await expect(readPipelineArtifact('quality_metrics.json', missingDir)).resolves.toBeNull();
  });

  it('falla con SyntaxError si el artefacto existe pero está corrupto', async () => {
    await writeFile(path.join(directory, 'quality_metrics.json'), '{ esto no es json', 'utf-8');

    await expect(readPipelineArtifact('quality_metrics.json', directory)).rejects.toBeInstanceOf(
      SyntaxError,
    );
  });
});
