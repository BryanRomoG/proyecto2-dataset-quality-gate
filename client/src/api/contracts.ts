import type { z } from 'zod';
import {
  type QualityReport,
  type SplitsReport,
  type VersionsReport,
  qualityReportSchema,
  splitsReportSchema,
  versionsReportSchema,
} from '../features/contracts/schemas';

// La UI nunca lee `contracts/examples/*.json` del disco ni lo importa al
// bundle: todo pasa por /api/contracts/*, igual que el resto de pantallas.
// Cuando T-204 cambie la fuente a datos reales, cambia el handler del
// server; esta capa no se entera.

async function getJson<T>(url: string, schema: z.ZodType<T>): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`No se pudo cargar ${url} (status ${response.status})`);
  }
  return schema.parse(await response.json());
}

export function fetchQualityContract(): Promise<QualityReport> {
  return getJson('/api/contracts/quality', qualityReportSchema);
}

export function fetchSplitsContract(): Promise<SplitsReport> {
  return getJson('/api/contracts/splits', splitsReportSchema);
}

export function fetchVersionsContract(): Promise<VersionsReport> {
  return getJson('/api/contracts/versions', versionsReportSchema);
}
