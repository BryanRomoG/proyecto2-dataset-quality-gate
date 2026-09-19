import type { Coco, QualityMetrics } from './schemas';

// Resuelve los ids que reportan los analizadores (anotaciones, imágenes) a
// algo que la UI pueda mostrar: nombre de archivo, tamaño, caja y clase.
// El analizador solo entrega ids; sin esto las "muestras ofensoras" serían
// una lista de números que nadie puede abrir.

export type ImageRef = { imageId: number; fileName: string; width: number; height: number };

export type AnnotationSample = ImageRef & {
  annotationId: number;
  category: string;
  bbox: [number, number, number, number];
  reasons: string[];
};

export type DuplicateSample = {
  hashDistance: number;
  similarity: number;
  a: ImageRef;
  b: ImageRef;
};

export type AnalyzerSamples = {
  small: AnnotationSample[];
  invalid: AnnotationSample[];
  duplicates: DuplicateSample[];
};

export function resolveAnalyzerSamples(coco: Coco, metrics: QualityMetrics): AnalyzerSamples {
  const imageById = new Map(coco.images.map((image) => [image.id, image]));
  const annotationById = new Map(coco.annotations.map((annotation) => [annotation.id, annotation]));
  const categoryName = new Map(coco.categories.map((category) => [category.id, category.name]));

  function imageRef(imageId: number): ImageRef | null {
    const image = imageById.get(imageId);
    return image
      ? { imageId, fileName: image.file_name, width: image.width, height: image.height }
      : null;
  }

  function annotationSample(annotationId: number, reasons: string[]): AnnotationSample | null {
    const annotation = annotationById.get(annotationId);
    const image = annotation ? imageRef(annotation.image_id) : null;
    if (!annotation || !image) return null;
    return {
      ...image,
      annotationId,
      category: categoryName.get(annotation.category_id) ?? 'unknown',
      bbox: annotation.bbox,
      reasons,
    };
  }

  const isPresent = <T>(value: T | null): value is T => value !== null;

  const small = metrics.small_objects.offending_sample_ids
    .map((id) => annotationSample(id, ['below_threshold']))
    .filter(isPresent);

  const invalid = metrics.invalid_boxes.invalid
    .map((box) => annotationSample(box.annotation_id, box.reasons))
    .filter(isPresent);

  const duplicates = metrics.duplicates.pairs
    .map((pair): DuplicateSample | null => {
      const a = imageRef(pair.image_id_a);
      const b = imageRef(pair.image_id_b);
      return a && b
        ? { hashDistance: pair.hash_distance, similarity: pair.similarity, a, b }
        : null;
    })
    .filter(isPresent);

  return { small, invalid, duplicates };
}
