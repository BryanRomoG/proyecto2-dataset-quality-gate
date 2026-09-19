import { readFile } from 'node:fs/promises';
import path from 'node:path';
import request from 'supertest';
import { describe, expect, it } from 'vitest';
import { createApiApp } from '../app';
import { CONTRACT_NAMES } from './contracts';

// T-104: la pantalla de contratos se monta contra los JSON congelados en
// T-101. Estos tests fijan la única garantía que la UI necesita del server:
// lo que responde /api/contracts/:name es exactamente el archivo congelado,
// sin normalizar ni recortar nada.

const app = createApiApp();
const examplesDir = path.resolve(process.cwd(), 'contracts/examples');

async function readExample(name: string): Promise<unknown> {
  return JSON.parse(await readFile(path.join(examplesDir, `${name}.json`), 'utf-8'));
}

describe('GET /api/contracts/:name', () => {
  it.each(CONTRACT_NAMES)('devuelve %s.json tal cual está congelado', async (name) => {
    const response = await request(app).get(`/api/contracts/${name}`);

    expect(response.status).toBe(200);
    expect(response.body).toEqual(await readExample(name));
  });

  it('responde 404 con la lista de contratos disponibles si el nombre no existe', async () => {
    const response = await request(app).get('/api/contracts/inventado');

    expect(response.status).toBe(404);
    expect(response.body.error).toContain('quality');
  });

  it('no permite salirse de contracts/examples/ por el nombre del contrato', async () => {
    // El nombre se resuelve contra una lista blanca: aunque llegue ya
    // decodificado, nunca se concatena a una ruta de disco.
    const response = await request(app).get('/api/contracts/..%2F..%2F.env');

    expect(response.status).toBe(404);
  });
});
