import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { type NextFunction, type Response, Router } from 'express';

// T-104: sirve los 3 contratos congelados por Bryan en T-101 (quality.json,
// splits.json, versions.json) tal cual, sin tocar su contenido ni inventar
// datos — son ejemplos congelados, todavía no datos reales (eso es T-204).

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const contractsDir = path.resolve(__dirname, '../../../contracts/examples');

export const contractsRouter = Router();

async function serveContract(filename: string, res: Response, next: NextFunction) {
  try {
    const raw = await readFile(path.join(contractsDir, filename), 'utf-8');
    res.status(200).type('application/json').send(raw);
  } catch (error) {
    next(error);
  }
}

contractsRouter.get('/quality', (_req, res, next) => serveContract('quality.json', res, next));
contractsRouter.get('/splits', (_req, res, next) => serveContract('splits.json', res, next));
contractsRouter.get('/versions', (_req, res, next) => serveContract('versions.json', res, next));
