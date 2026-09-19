import request from 'supertest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createApiApp } from '../app';
import { readPipelineArtifact } from '../lib/pipeline-artifacts';

// T-204: GET /api/dashboard/quality-metrics expone la salida real de los
// analizadores (T-202). Se mockea el lector de artefactos —no el disco— para
// que estas pruebas no dependan de si esta máquina ya corrió `dvc pull`.
vi.mock('../lib/pipeline-artifacts', () => ({
  readPipelineArtifact: vi.fn(),
  artifactRelativePath: (fileName: string) => `data/processed/${fileName}`,
}));

const readArtifactMock = vi.mocked(readPipelineArtifact);
const app = createApiApp();

const metrics = {
  small_objects: { threshold_px: 32, small_count: 18 },
  class_imbalance: { counts: { car: 214, person: 208 } },
};

beforeEach(() => {
  readArtifactMock.mockReset();
});

describe('GET /api/dashboard/quality-metrics', () => {
  it('sirve el artefacto del pipeline tal cual, con su fecha de generación', async () => {
    readArtifactMock.mockResolvedValue({
      path: 'data/processed/quality_metrics.json',
      generatedAt: '2026-09-18T09:30:00.000Z',
      data: metrics,
    });

    const response = await request(app).get('/api/dashboard/quality-metrics');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({
      generatedAt: '2026-09-18T09:30:00.000Z',
      source: 'data/processed/quality_metrics.json',
      metrics,
    });
  });

  it('responde 503 con la ruta esperada y el comando que falta si el artefacto no existe', async () => {
    readArtifactMock.mockResolvedValue(null);

    const response = await request(app).get('/api/dashboard/quality-metrics');

    // 503 y no 404/200-con-ceros: el dato no está, y la UI tiene que poder
    // decir por qué en vez de mostrar métricas vacías como si fueran reales.
    expect(response.status).toBe(503);
    expect(response.body.expectedPath).toBe('data/processed/quality_metrics.json');
    expect(response.body.hint).toContain('dvc');
  });

  it('nombra el archivo corrupto en vez de un "error interno" genérico', async () => {
    readArtifactMock.mockRejectedValue(new SyntaxError('Unexpected token e in JSON at position 2'));

    const response = await request(app).get('/api/dashboard/quality-metrics');

    expect(response.status).toBe(500);
    expect(response.body.error).toContain('quality_metrics.json');
    expect(response.body.error).toContain('no es JSON válido');
  });
});
