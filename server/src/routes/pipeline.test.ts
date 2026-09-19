import { mkdtemp, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import request from 'supertest';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { createApiApp } from '../app';
import { readPipelineArtifact } from '../lib/pipeline-artifacts';

// Las pantallas de la sección 7 leen artefactos del pipeline. Se mockea el
// lector (no el disco) para no depender de si esta máquina ya hizo `dvc pull`,
// y las rutas de quality.yaml / imágenes apuntan a una carpeta temporal.
vi.mock('../lib/pipeline-artifacts', () => ({
  readPipelineArtifact: vi.fn(),
  artifactRelativePath: (fileName: string) => `data/processed/${fileName}`,
}));

const paths = vi.hoisted(() => ({ policy: '', images: '' }));
vi.mock('../pipeline/paths', () => ({
  policyPath: () => paths.policy,
  rawImagesDir: () => paths.images,
}));

const readArtifactMock = vi.mocked(readPipelineArtifact);
const app = createApiApp();

const coco = {
  categories: [
    { id: 1, name: 'car' },
    { id: 2, name: 'person' },
  ],
  images: [
    { id: 1, file_name: 'a.jpg', width: 200, height: 200 },
    { id: 2, file_name: 'b.jpg', width: 200, height: 200 },
  ],
  annotations: [
    { id: 10, image_id: 1, category_id: 1, bbox: [0, 0, 10, 10] },
    { id: 11, image_id: 2, category_id: 2, bbox: [0, 0, 0, 30] },
  ],
};

function metricsBody(counts: Record<string, number> = { car: 317, person: 362 }) {
  return {
    small_objects: {
      threshold_px: 32,
      total_annotations: 2,
      small_count: 1,
      percentage_below_threshold: 50,
      most_affected_category: 'car',
      offending_sample_ids: [10],
    },
    class_imbalance: {
      counts,
      majority_minority_ratio: 1.14,
      classes_below_minimum: Object.entries(counts)
        .filter(([, count]) => count < 300)
        .map(([name]) => name),
    },
    invalid_boxes: {
      total_annotations: 2,
      invalid: [{ annotation_id: 11, reasons: ['zero_width'] }],
    },
    spatial_bias: { count: 2, mean: 100, median: 90, p10: 10, p25: 20, p75: 150, p90: 200 },
    duplicates: {
      distance_threshold: 8,
      pairs: [{ image_id_a: 1, image_id_b: 2, hash_distance: 3, similarity: 0.95 }],
    },
  };
}

function serve(files: Record<string, unknown>) {
  readArtifactMock.mockImplementation(async (fileName: string) => {
    if (!(fileName in files)) return null;
    return {
      path: `data/processed/${fileName}`,
      generatedAt: '2026-09-18T09:30:00.000Z',
      data: files[fileName],
    };
  });
}

let dir: string;

beforeEach(async () => {
  readArtifactMock.mockReset();
  dir = await mkdtemp(path.join(tmpdir(), 'pipeline-routes-'));
  paths.policy = path.join(dir, 'quality.yaml');
  paths.images = dir;
  await writeFile(
    paths.policy,
    'checks:\n  min_images_per_class:\n    threshold: 300\n    severity: fail\n',
    'utf-8',
  );
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

describe('GET /api/pipeline/gate', () => {
  it('evalúa la política de quality.yaml contra la telemetría real', async () => {
    serve({ 'quality_metrics.json': metricsBody() });

    const response = await request(app).get('/api/pipeline/gate');

    expect(response.status).toBe(200);
    expect(response.body.passed).toBe(true);
    expect(response.body.checks[0]).toMatchObject({ name: 'min_images_per_class', value: 317 });
  });

  it('bloquea cuando una clase queda bajo el umbral', async () => {
    serve({ 'quality_metrics.json': metricsBody({ car: 214, person: 362 }) });

    const response = await request(app).get('/api/pipeline/gate');

    expect(response.body.passed).toBe(false);
    expect(response.body.failedChecks).toBe(1);
  });

  it('responde 503 con el comando que falta si el pipeline no dejó el artefacto', async () => {
    serve({});

    const response = await request(app).get('/api/pipeline/gate');

    expect(response.status).toBe(503);
    expect(response.body.expectedPath).toBe('data/processed/quality_metrics.json');
    expect(response.body.hint).toContain('dvc');
  });

  it('nombra el archivo y el campo cuando el artefacto cambió de forma', async () => {
    serve({ 'quality_metrics.json': { small_objects: {} } });

    const response = await request(app).get('/api/pipeline/gate');

    expect(response.status).toBe(500);
    expect(response.body.error).toContain('quality_metrics.json');
  });
});

describe('GET /api/pipeline/analyzers', () => {
  it('devuelve las métricas y las muestras resueltas a imagen + caja', async () => {
    serve({ 'quality_metrics.json': metricsBody(), 'coco.validated.json': coco });

    const response = await request(app).get('/api/pipeline/analyzers');

    expect(response.status).toBe(200);
    expect(response.body.metrics.small_objects.small_count).toBe(1);
    expect(response.body.samples.small[0]).toMatchObject({ fileName: 'a.jpg', category: 'car' });
    expect(response.body.samples.invalid[0].reasons).toEqual(['zero_width']);
    expect(response.body.samples.duplicates[0].b.fileName).toBe('b.jpg');
  });
});

describe('GET /api/pipeline/splits', () => {
  it('agrega la distribución por clase y detecta la fuga de un par cruzado', async () => {
    serve({
      'quality_metrics.json': metricsBody(),
      'coco.validated.json': coco,
      'splits.json': {
        seed: 42,
        ratios: { train: 0.5, val: 0.25, test: 0.25 },
        assignments: { '1': 'train', '2': 'val' },
        counts: { train: 1, val: 1, test: 0 },
      },
    });

    const response = await request(app).get('/api/pipeline/splits');

    expect(response.status).toBe(200);
    expect(response.body.report.leakage.ok).toBe(false);
    expect(response.body.report.leakage.crossSplitPairs).toHaveLength(1);
    expect(response.body.report.classes).toHaveLength(2);
  });
});

describe('GET /api/pipeline/versions y /embedding', () => {
  it('responden 503 con el comando que genera cada artefacto', async () => {
    serve({});

    const versions = await request(app).get('/api/pipeline/versions');
    const embedding = await request(app).get('/api/pipeline/embedding');

    expect(versions.status).toBe(503);
    expect(versions.body.hint).toContain('build_versions.py');
    expect(embedding.status).toBe(503);
    expect(embedding.body.hint).toContain('embed.py');
  });

  it('sirven el artefacto validado', async () => {
    serve({
      'versions.json': {
        current: 'v1.0.0',
        releases: [
          {
            version: 'v1.0.0',
            message: 'release',
            created_at: '2026-09-18T00:00:00Z',
            commit: 'abc1234',
            dataset_md5: 'c500a26a',
            snapshot: null,
            remotes: { dev: 'in_sync', prod: 'in_sync' },
            diff_vs_previous: null,
          },
        ],
      },
    });

    const response = await request(app).get('/api/pipeline/versions');

    expect(response.status).toBe(200);
    expect(response.body.versions.releases[0].remotes.prod).toBe('in_sync');
  });
});

describe('Settings: GET / PUT /api/pipeline/settings', () => {
  it('PUT persiste en quality.yaml y devuelve la compuerta re-evaluada', async () => {
    serve({ 'quality_metrics.json': metricsBody() });

    const put = await request(app)
      .put('/api/pipeline/settings')
      .send({ checks: { min_images_per_class: { threshold: 999, severity: 'fail' } } });

    expect(put.status).toBe(200);
    expect(put.body.gate.passed).toBe(false);

    // Persistió de verdad: una lectura nueva, y la compuerta, lo reflejan.
    const get = await request(app).get('/api/pipeline/settings');
    expect(get.body.policy.checks.min_images_per_class.threshold).toBe(999);

    const gate = await request(app).get('/api/pipeline/gate');
    expect(gate.body.passed).toBe(false);
  });

  it('PUT rechaza un umbral inválido con 422 y no modifica el archivo', async () => {
    const response = await request(app)
      .put('/api/pipeline/settings')
      .send({ checks: { min_images_per_class: { threshold: -5, severity: 'fail' } } });

    expect(response.status).toBe(422);

    const get = await request(app).get('/api/pipeline/settings');
    expect(get.body.policy.checks.min_images_per_class.threshold).toBe(300);
  });
});

describe('GET /api/pipeline/images/:fileName', () => {
  it('sirve una imagen que existe', async () => {
    await writeFile(path.join(dir, 'a.jpg'), Buffer.from([0xff, 0xd8, 0xff]));

    const response = await request(app).get('/api/pipeline/images/a.jpg');

    expect(response.status).toBe(200);
  });

  it('responde 404 con el comando que falta si la imagen no está materializada', async () => {
    const response = await request(app).get('/api/pipeline/images/nada.jpg');

    expect(response.status).toBe(404);
    expect(response.body.error).toContain('dvc pull');
  });

  it.each(['..%2F..%2F.env', '..%5Csecreto.jpg', 'notas.txt', '.env'])(
    'rechaza %s (no puede salirse de la carpeta ni servir otros tipos)',
    async (name) => {
      const response = await request(app).get(`/api/pipeline/images/${name}`);

      expect(response.status).toBe(400);
    },
  );
});
