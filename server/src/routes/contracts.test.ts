import request from 'supertest';
import { describe, expect, it } from 'vitest';
import { createApiApp } from '../app';

// T-104: estos endpoints solo sirven los JSON congelados de contracts/examples
// tal cual (sin BD) — por eso no comparten setup con dashboard.test.ts.

const app = createApiApp();

describe('GET /api/contracts/quality', () => {
  it('sirve quality.json tal cual, sin transformarlo', async () => {
    const response = await request(app).get('/api/contracts/quality');

    expect(response.status).toBe(200);
    expect(response.body.passed).toBe(false);
    expect(Array.isArray(response.body.checks)).toBe(true);
    expect(response.body.checks[0]).toMatchObject({ name: 'min_images_per_class' });
  });
});

describe('GET /api/contracts/splits', () => {
  it('sirve splits.json tal cual, sin transformarlo', async () => {
    const response = await request(app).get('/api/contracts/splits');

    expect(response.status).toBe(200);
    expect(response.body.seed).toBe(42);
    expect(response.body.ratios).toMatchObject({ train: 0.7, val: 0.15, test: 0.15 });
    expect(response.body.counts).toMatchObject({ train: 4, val: 1, test: 1 });
  });
});

describe('GET /api/contracts/versions', () => {
  it('sirve versions.json tal cual, sin transformarlo', async () => {
    const response = await request(app).get('/api/contracts/versions');

    expect(response.status).toBe(200);
    expect(response.body.current).toBe('v0.2.0');
    expect(response.body.releases).toHaveLength(2);
    expect(response.body.releases[1].diff_vs_previous).toMatchObject({
      from: 'v0.1.0',
      to: 'v0.2.0',
    });
  });
});
