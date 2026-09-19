import { readFileSync } from 'node:fs';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { qualityReportSchema, splitsReportSchema, versionsReportSchema } from './schemas';

// Guarda contra deriva de contrato: si Bryan publica una versión nueva de
// los JSON congelados (T-101) con una forma distinta, este test se pone en
// rojo aquí — antes de que la pantalla renderice campos vacíos en silencio.

function readFrozenContract(name: string): unknown {
  const filePath = path.resolve(process.cwd(), 'contracts/examples', `${name}.json`);
  return JSON.parse(readFileSync(filePath, 'utf-8'));
}

describe('contratos congelados (T-101)', () => {
  it('quality.json cumple el esquema que espera la pantalla', () => {
    const report = qualityReportSchema.parse(readFrozenContract('quality'));

    // No es solo un booleano: cada check trae valor, umbral y severidad.
    expect(report.checks.length).toBeGreaterThan(0);
    for (const check of report.checks) {
      expect(typeof check.value).toBe('number');
      expect(typeof check.threshold).toBe('number');
    }
  });

  it('splits.json cumple el esquema y sus counts cuadran con las asignaciones', () => {
    const report = splitsReportSchema.parse(readFrozenContract('splits'));
    const assigned = Object.values(report.assignments);

    expect(report.counts.train + report.counts.val + report.counts.test).toBe(assigned.length);
  });

  it('versions.json cumple el esquema y la versión actual existe en el historial', () => {
    const report = versionsReportSchema.parse(readFrozenContract('versions'));

    expect(report.releases.map((release) => release.version)).toContain(report.current);
  });
});
