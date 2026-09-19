import { readFile, rename, writeFile } from 'node:fs/promises';
import { parseDocument } from 'yaml';
import { type QualityPolicy, qualityPolicySchema } from './schemas';

// Lectura y escritura de quality.yaml para la pantalla Settings. Igual que
// en Python, el YAML nunca se usa como objeto crudo: siempre pasa por el
// esquema (qualityPolicySchema, espejo de QualityPolicy).

export class PolicyValidationError extends Error {
  constructor(public readonly issues: string[]) {
    super(`quality.yaml inválido: ${issues.join('; ')}`);
    this.name = 'PolicyValidationError';
  }
}

export function parsePolicy(text: string): QualityPolicy {
  const parsed = qualityPolicySchema.safeParse(parseDocument(text).toJS());
  if (!parsed.success) {
    throw new PolicyValidationError(
      parsed.error.issues.map((issue) => `${issue.path.join('.') || '(raíz)'}: ${issue.message}`),
    );
  }
  return parsed.data;
}

export async function readPolicy(filePath: string): Promise<QualityPolicy> {
  return parsePolicy(await readFile(filePath, 'utf-8'));
}

/**
 * Aplica `next` sobre el quality.yaml que ya existe: solo cambia el umbral y
 * la severidad de los checks declarados, y conserva comentarios y orden del
 * archivo (el equipo documenta ahí de dónde salió cada umbral). Un check que
 * no existe todavía en el archivo se rechaza: Settings edita la política, no
 * inventa analizadores nuevos.
 */
export async function writePolicy(filePath: string, next: unknown): Promise<QualityPolicy> {
  const validated = qualityPolicySchema.safeParse(next);
  if (!validated.success) {
    throw new PolicyValidationError(
      validated.error.issues.map(
        (issue) => `${issue.path.join('.') || '(raíz)'}: ${issue.message}`,
      ),
    );
  }

  const current = parseDocument(await readFile(filePath, 'utf-8'));
  const known = new Set(Object.keys(qualityPolicySchema.parse(current.toJS()).checks));
  const unknown = Object.keys(validated.data.checks).filter((name) => !known.has(name));
  if (unknown.length > 0) {
    throw new PolicyValidationError(
      unknown.map(
        (name) => `checks.${name}: no existe en quality.yaml, no se puede crear desde la UI`,
      ),
    );
  }

  for (const [name, check] of Object.entries(validated.data.checks)) {
    current.setIn(['checks', name, 'threshold'], check.threshold);
    current.setIn(['checks', name, 'severity'], check.severity);
  }

  // Escritura atómica: un crash a medias no deja un quality.yaml truncado
  // que rompería la compuerta y `dvc repro` para todo el equipo.
  const tempPath = `${filePath}.tmp`;
  await writeFile(tempPath, String(current), 'utf-8');
  await rename(tempPath, filePath);

  return readPolicy(filePath);
}
