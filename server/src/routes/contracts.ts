import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Router } from 'express';

export const contractsRouter = Router();

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const examplesDir = path.resolve(__dirname, '../../../contracts/examples');

// T-104: la pantalla de contratos todavía no lee salidas reales del
// pipeline, consume los contratos congelados en T-101 (`contracts/examples/`).
// Este router los sirve **tal cual**: no normaliza llaves, no rellena
// defaults ni reordena nada. Así, si Bryan cambia la forma de un contrato,
// el cambio se ve en la pantalla (o truena la validación Zod del cliente)
// en vez de quedar enmascarado por una capa de traducción intermedia.
// En T-204 estos handlers cambian de fuente (data/processed/ o BD) sin que
// la UI tenga que cambiar de URL.
const CONTRACT_FILES = {
  quality: 'quality.json',
  splits: 'splits.json',
  versions: 'versions.json',
} as const;

export type ContractName = keyof typeof CONTRACT_FILES;

export const CONTRACT_NAMES = Object.keys(CONTRACT_FILES) as ContractName[];

function isContractName(value: string): value is ContractName {
  return Object.hasOwn(CONTRACT_FILES, value);
}

export async function readFrozenContract(name: ContractName): Promise<unknown> {
  // Se lee del disco en cada request (no se cachea en memoria al arrancar):
  // durante Fase 1 los JSON congelados todavía pueden actualizarse y la
  // pantalla debe reflejarlo con un refresh, sin reiniciar el server.
  const raw = await readFile(path.join(examplesDir, CONTRACT_FILES[name]), 'utf-8');
  return JSON.parse(raw);
}

// El nombre se resuelve contra una lista blanca, no se concatena a la ruta:
// `GET /api/contracts/../../.env` no puede salirse de contracts/examples/.
contractsRouter.get('/:name', async (req, res, next) => {
  const { name } = req.params;
  if (!isContractName(name)) {
    res.status(404).json({
      error: `Contrato "${name}" no existe. Disponibles: ${CONTRACT_NAMES.join(', ')}.`,
    });
    return;
  }

  try {
    res.status(200).json(await readFrozenContract(name));
  } catch (error) {
    next(error);
  }
});
