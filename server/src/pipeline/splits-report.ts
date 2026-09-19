import type { Coco, QualityMetrics, SplitName, SplitsArtifact } from './schemas';

// Lo que muestra la pantalla Splits: distribución de clases por partición y
// el resultado del chequeo de fuga. Todo se deriva de artefactos ya escritos
// (coco.validated.json, splits.json, quality_metrics.json); aquí solo se
// agrega y se verifica, no se vuelve a hacer el split.

const SPLIT_NAMES: SplitName[] = ['train', 'val', 'test'];

export type ClassDistribution = {
  className: string;
  train: number;
  val: number;
  test: number;
  total: number;
};

export type LeakedPair = {
  imageIdA: number;
  imageIdB: number;
  splitA: SplitName;
  splitB: SplitName;
  hashDistance: number;
};

export type SplitsReport = {
  seed: number;
  ratios: Record<string, number>;
  /** Imágenes por split contadas desde `assignments` (no se confía en `counts`). */
  imagesPerSplit: Record<SplitName, number>;
  /** Proporción real de cada split sobre el total de imágenes asignadas. */
  actualRatios: Record<SplitName, number>;
  classes: ClassDistribution[];
  leakage: {
    /** true solo si no hay pares duplicados repartidos entre splits ni imágenes sin split. */
    ok: boolean;
    duplicatePairsChecked: number;
    crossSplitPairs: LeakedPair[];
    /** Imágenes del COCO que no recibieron split. */
    unassignedImages: number[];
    /** Ids en `splits.json` que no existen en el COCO. */
    unknownImages: number[];
    /** true si `counts` del artefacto coincide con lo recontado desde `assignments`. */
    countsConsistent: boolean;
  };
};

export function buildSplitsReport(
  coco: Coco,
  splits: SplitsArtifact,
  metrics: QualityMetrics,
): SplitsReport {
  const splitOf = new Map<number, SplitName>();
  for (const [imageId, split] of Object.entries(splits.assignments)) {
    splitOf.set(Number(imageId), split);
  }

  const imagesPerSplit: Record<SplitName, number> = { train: 0, val: 0, test: 0 };
  for (const split of splitOf.values()) {
    imagesPerSplit[split] += 1;
  }
  const assignedTotal = splitOf.size;
  const actualRatios: Record<SplitName, number> = {
    train: assignedTotal === 0 ? 0 : imagesPerSplit.train / assignedTotal,
    val: assignedTotal === 0 ? 0 : imagesPerSplit.val / assignedTotal,
    test: assignedTotal === 0 ? 0 : imagesPerSplit.test / assignedTotal,
  };

  // Imágenes DISTINTAS con al menos una caja de la clase, por split: la misma
  // regla de conteo que M3 (una imagen con 7 coches cuenta 1).
  const categoryName = new Map(coco.categories.map((category) => [category.id, category.name]));
  const imagesByClass = new Map<string, Set<number>>();
  for (const annotation of coco.annotations) {
    const name = categoryName.get(annotation.category_id);
    if (name === undefined) continue;
    const images = imagesByClass.get(name) ?? new Set<number>();
    images.add(annotation.image_id);
    imagesByClass.set(name, images);
  }

  const classes: ClassDistribution[] = [...imagesByClass.entries()]
    .map(([className, imageIds]) => {
      const row: ClassDistribution = { className, train: 0, val: 0, test: 0, total: 0 };
      for (const imageId of imageIds) {
        const split = splitOf.get(imageId);
        if (split === undefined) continue;
        row[split] += 1;
        row.total += 1;
      }
      return row;
    })
    .sort((a, b) => a.className.localeCompare(b.className));

  const crossSplitPairs: LeakedPair[] = [];
  for (const pair of metrics.duplicates.pairs) {
    const splitA = splitOf.get(pair.image_id_a);
    const splitB = splitOf.get(pair.image_id_b);
    if (splitA !== undefined && splitB !== undefined && splitA !== splitB) {
      crossSplitPairs.push({
        imageIdA: pair.image_id_a,
        imageIdB: pair.image_id_b,
        splitA,
        splitB,
        hashDistance: pair.hash_distance,
      });
    }
  }

  const cocoImageIds = new Set(coco.images.map((image) => image.id));
  const unassignedImages = coco.images.filter((image) => !splitOf.has(image.id)).map((i) => i.id);
  const unknownImages = [...splitOf.keys()].filter((id) => !cocoImageIds.has(id));

  const countsConsistent = SPLIT_NAMES.every(
    (name) => (splits.counts[name] ?? 0) === imagesPerSplit[name],
  );

  return {
    seed: splits.seed,
    ratios: splits.ratios,
    imagesPerSplit,
    actualRatios,
    classes,
    leakage: {
      ok:
        crossSplitPairs.length === 0 && unassignedImages.length === 0 && unknownImages.length === 0,
      duplicatePairsChecked: metrics.duplicates.pairs.length,
      crossSplitPairs,
      unassignedImages,
      unknownImages,
      countsConsistent,
    },
  };
}
