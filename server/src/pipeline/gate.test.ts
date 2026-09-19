import { describe, expect, it } from 'vitest';
import { evaluateGate } from './gate';
import type { QualityMetrics, QualityPolicy } from './schemas';

function metricsWith(overrides: {
  counts?: Record<string, number>;
  invalid?: Array<{ annotation_id: number; reasons: string[] }>;
}): QualityMetrics {
  const counts = overrides.counts ?? { car: 317, person: 362 };
  return {
    small_objects: {
      threshold_px: 32,
      total_annotations: 10,
      small_count: 0,
      percentage_below_threshold: 0,
      most_affected_category: null,
      offending_sample_ids: [],
    },
    class_imbalance: {
      counts,
      majority_minority_ratio: 1,
      classes_below_minimum: Object.entries(counts)
        .filter(([, count]) => count < 300)
        .map(([name]) => name),
    },
    invalid_boxes: { total_annotations: 10, invalid: overrides.invalid ?? [] },
    spatial_bias: { count: 10, mean: 1, median: 1, p10: 1, p25: 1, p75: 1, p90: 1 },
    duplicates: { distance_threshold: 8, pairs: [] },
  };
}

const policy: QualityPolicy = {
  checks: {
    min_images_per_class: { threshold: 300, severity: 'fail' },
    invalid_boxes_count: { threshold: 5, severity: 'warn' },
  },
};

describe('evaluateGate', () => {
  it('pasa cuando la clase más chica alcanza el umbral', () => {
    const report = evaluateGate(policy, metricsWith({}));

    expect(report.passed).toBe(true);
    expect(report.failedChecks).toBe(0);
    expect(report.checks[0]).toMatchObject({ name: 'min_images_per_class', value: 317 });
  });

  it('bloquea cuando un check fail no llega al umbral y nombra las clases ofensoras', () => {
    const report = evaluateGate(policy, metricsWith({ counts: { car: 214, person: 362 } }));

    expect(report.passed).toBe(false);
    expect(report.failedChecks).toBe(1);
    expect(report.checks[0]?.offendingSamples).toEqual(['car']);
  });

  it('cambiar el umbral en la política cambia el resultado sin tocar los datos', () => {
    const strict: QualityPolicy = {
      checks: { min_images_per_class: { threshold: 999, severity: 'fail' } },
    };

    expect(evaluateGate(strict, metricsWith({})).passed).toBe(false);
  });

  it('las clases ofensoras se recalculan contra el umbral vigente, no contra el de la corrida del pipeline', () => {
    // El pipeline corrió con umbral 300 (classes_below_minimum = []), pero
    // Settings subió el umbral a 340: car (317) ahora es ofensora.
    const raised: QualityPolicy = {
      checks: { min_images_per_class: { threshold: 340, severity: 'fail' } },
    };
    const report = evaluateGate(raised, metricsWith({}));

    expect(report.passed).toBe(false);
    expect(report.checks[0]?.offendingSamples).toEqual(['car']);
  });

  it('un warn en rojo se reporta pero no bloquea', () => {
    const invalid = Array.from({ length: 6 }, (_, i) => ({
      annotation_id: i + 1,
      reasons: ['zero_width'],
    }));
    const report = evaluateGate(policy, metricsWith({ invalid }));

    expect(report.passed).toBe(true);
    expect(report.warnings).toBe(1);
    expect(report.failedChecks).toBe(1);
    expect(report.checks[1]?.offendingSamples).toHaveLength(6);
  });

  it('respeta la frontera: valor == umbral pasa en gte y en lte', () => {
    const edge: QualityPolicy = {
      checks: {
        min_images_per_class: { threshold: 317, severity: 'fail' },
        invalid_boxes_count: { threshold: 0, severity: 'fail' },
      },
    };

    expect(evaluateGate(edge, metricsWith({})).passed).toBe(true);
  });

  it('un check sin analizador no pasa en silencio', () => {
    const unknown: QualityPolicy = {
      checks: {
        min_images_per_class: { threshold: 300, severity: 'fail' },
        blur_score: { threshold: 1, severity: 'fail' },
      },
    };
    const report = evaluateGate(unknown, metricsWith({}));

    expect(report.passed).toBe(false);
    expect(report.checks[1]).toMatchObject({ name: 'blur_score', evaluated: false, passed: false });
  });

  it('sin clases el mínimo es 0 y la compuerta bloquea', () => {
    expect(evaluateGate(policy, metricsWith({ counts: {} })).passed).toBe(false);
  });
});
