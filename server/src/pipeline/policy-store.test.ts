import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { PolicyValidationError, readPolicy, writePolicy } from './policy-store';

const YAML_WITH_COMMENTS = `# Política de la compuerta (M3 del curso: 300 imágenes por clase).
checks:
  min_images_per_class:
    threshold: 300
    severity: fail
  invalid_boxes_count:
    threshold: 5
    severity: warn
`;

let dir: string;
let file: string;

beforeEach(async () => {
  dir = await mkdtemp(path.join(tmpdir(), 'quality-policy-'));
  file = path.join(dir, 'quality.yaml');
  await writeFile(file, YAML_WITH_COMMENTS, 'utf-8');
});

afterEach(async () => {
  await rm(dir, { recursive: true, force: true });
});

describe('readPolicy', () => {
  it('lee umbral y severidad de cada check', async () => {
    expect(await readPolicy(file)).toEqual({
      checks: {
        min_images_per_class: { threshold: 300, severity: 'fail' },
        invalid_boxes_count: { threshold: 5, severity: 'warn' },
      },
    });
  });

  it('rechaza un quality.yaml sin min_images_per_class', async () => {
    await writeFile(
      file,
      'checks:\n  invalid_boxes_count:\n    threshold: 5\n    severity: warn\n',
    );

    await expect(readPolicy(file)).rejects.toBeInstanceOf(PolicyValidationError);
  });
});

describe('writePolicy', () => {
  it('persiste el cambio en el archivo y la siguiente lectura lo refleja', async () => {
    await writePolicy(file, {
      checks: {
        min_images_per_class: { threshold: 999, severity: 'fail' },
        invalid_boxes_count: { threshold: 5, severity: 'fail' },
      },
    });

    const reread = await readPolicy(file);
    expect(reread.checks.min_images_per_class?.threshold).toBe(999);
    expect(reread.checks.invalid_boxes_count?.severity).toBe('fail');
  });

  it('conserva los comentarios del archivo', async () => {
    await writePolicy(file, {
      checks: {
        min_images_per_class: { threshold: 350, severity: 'fail' },
        invalid_boxes_count: { threshold: 5, severity: 'warn' },
      },
    });

    expect(await readFile(file, 'utf-8')).toContain('# Política de la compuerta');
  });

  it.each([
    ['umbral negativo', { threshold: -1, severity: 'fail' }],
    ['severidad inventada', { threshold: 300, severity: 'critical' }],
    ['umbral no numérico', { threshold: 'mucho', severity: 'fail' }],
  ])('rechaza %s sin tocar el archivo', async (_label, badCheck) => {
    await expect(
      writePolicy(file, { checks: { min_images_per_class: badCheck } }),
    ).rejects.toBeInstanceOf(PolicyValidationError);

    expect(await readFile(file, 'utf-8')).toBe(YAML_WITH_COMMENTS);
  });

  it('rechaza crear un check nuevo desde la UI', async () => {
    await expect(
      writePolicy(file, {
        checks: {
          min_images_per_class: { threshold: 300, severity: 'fail' },
          blur_score: { threshold: 1, severity: 'fail' },
        },
      }),
    ).rejects.toThrow(/blur_score/);
  });

  it('rechaza una política sin min_images_per_class', async () => {
    await expect(
      writePolicy(file, { checks: { invalid_boxes_count: { threshold: 1, severity: 'warn' } } }),
    ).rejects.toBeInstanceOf(PolicyValidationError);
  });
});
