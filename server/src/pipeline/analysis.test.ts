import { describe, expect, it } from 'vitest';
import { resolveAnalyzerSamples } from './samples';
import type { Coco, QualityMetrics, SplitsArtifact } from './schemas';
import { buildSplitsReport } from './splits-report';

const coco: Coco = {
  categories: [
    { id: 1, name: 'car' },
    { id: 2, name: 'person' },
  ],
  images: [1, 2, 3, 4].map((id) => ({ id, file_name: `img-${id}.jpg`, width: 200, height: 100 })),
  annotations: [
    { id: 10, image_id: 1, category_id: 1, bbox: [0, 0, 10, 10] },
    { id: 11, image_id: 1, category_id: 1, bbox: [5, 5, 20, 20] },
    { id: 12, image_id: 2, category_id: 1, bbox: [0, 0, 50, 50] },
    { id: 13, image_id: 3, category_id: 2, bbox: [0, 0, 0, 40] },
    { id: 14, image_id: 4, category_id: 2, bbox: [0, 0, 40, 40] },
  ],
};

function metrics(pairs: QualityMetrics['duplicates']['pairs'] = []): QualityMetrics {
  return {
    small_objects: {
      threshold_px: 32,
      total_annotations: 5,
      small_count: 2,
      percentage_below_threshold: 40,
      most_affected_category: 'car',
      offending_sample_ids: [10, 999],
    },
    class_imbalance: {
      counts: { car: 2, person: 2 },
      majority_minority_ratio: 1,
      classes_below_minimum: [],
    },
    invalid_boxes: {
      total_annotations: 5,
      invalid: [{ annotation_id: 13, reasons: ['zero_width'] }],
    },
    spatial_bias: { count: 5, mean: 1, median: 1, p10: 1, p25: 1, p75: 1, p90: 1 },
    duplicates: { distance_threshold: 8, pairs },
  };
}

const splits: SplitsArtifact = {
  seed: 42,
  ratios: { train: 0.5, val: 0.25, test: 0.25 },
  assignments: { '1': 'train', '2': 'train', '3': 'val', '4': 'test' },
  counts: { train: 2, val: 1, test: 1 },
};

describe('buildSplitsReport', () => {
  it('cuenta imágenes distintas por clase y split (una imagen con 2 cajas cuenta 1)', () => {
    const report = buildSplitsReport(coco, splits, metrics());

    expect(report.classes).toEqual([
      { className: 'car', train: 2, val: 0, test: 0, total: 2 },
      { className: 'person', train: 0, val: 1, test: 1, total: 2 },
    ]);
    expect(report.imagesPerSplit).toEqual({ train: 2, val: 1, test: 1 });
    expect(report.actualRatios.train).toBe(0.5);
  });

  it('sin duplicados cruzados ni imágenes sueltas, la fuga es ok', () => {
    const report = buildSplitsReport(coco, splits, metrics());

    expect(report.leakage.ok).toBe(true);
    expect(report.leakage.countsConsistent).toBe(true);
  });

  it('un par de near-duplicates repartido entre splits se reporta como fuga', () => {
    const pair = { image_id_a: 1, image_id_b: 3, hash_distance: 2, similarity: 0.97 };
    const report = buildSplitsReport(coco, splits, metrics([pair]));

    expect(report.leakage.ok).toBe(false);
    expect(report.leakage.crossSplitPairs).toEqual([
      { imageIdA: 1, imageIdB: 3, splitA: 'train', splitB: 'val', hashDistance: 2 },
    ]);
  });

  it('un par de duplicados en el mismo split no es fuga', () => {
    const pair = { image_id_a: 1, image_id_b: 2, hash_distance: 0, similarity: 1 };

    expect(buildSplitsReport(coco, splits, metrics([pair])).leakage.ok).toBe(true);
  });

  it('detecta imágenes sin split, ids desconocidos y conteos incoherentes', () => {
    const broken: SplitsArtifact = {
      ...splits,
      assignments: { '1': 'train', '2': 'train', '3': 'val', '77': 'test' },
      counts: { train: 9, val: 1, test: 1 },
    };
    const report = buildSplitsReport(coco, broken, metrics());

    expect(report.leakage.unassignedImages).toEqual([4]);
    expect(report.leakage.unknownImages).toEqual([77]);
    expect(report.leakage.countsConsistent).toBe(false);
    expect(report.leakage.ok).toBe(false);
  });
});

describe('resolveAnalyzerSamples', () => {
  it('convierte ids de anotación en imagen + caja + clase y descarta ids que no existen', () => {
    const samples = resolveAnalyzerSamples(coco, metrics());

    expect(samples.small).toHaveLength(1);
    expect(samples.small[0]).toMatchObject({
      annotationId: 10,
      fileName: 'img-1.jpg',
      category: 'car',
      bbox: [0, 0, 10, 10],
    });
  });

  it('conserva las razones de las cajas inválidas', () => {
    const samples = resolveAnalyzerSamples(coco, metrics());

    expect(samples.invalid[0]).toMatchObject({ annotationId: 13, reasons: ['zero_width'] });
  });

  it('resuelve los pares de duplicados a sus dos imágenes', () => {
    const pair = { image_id_a: 1, image_id_b: 2, hash_distance: 3, similarity: 0.95 };
    const samples = resolveAnalyzerSamples(coco, metrics([pair]));

    expect(samples.duplicates[0]?.a.fileName).toBe('img-1.jpg');
    expect(samples.duplicates[0]?.b.fileName).toBe('img-2.jpg');
  });
});
