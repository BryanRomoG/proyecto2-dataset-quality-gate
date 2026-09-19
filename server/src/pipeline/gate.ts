import type { QualityMetrics, QualityPolicy } from './schemas';

// Evalúa la política de quality.yaml contra la telemetría que ya calculó el
// pipeline. Mismas reglas que `dataset_pipeline.quality_gate.evaluator`:
//   - cada check compara UN valor observado contra su umbral, en la dirección
//     que le corresponde (gte / lte);
//   - un `fail` que no pasa bloquea la compuerta; un `warn` solo se reporta.
// No recalcula analizadores: los valores salen de quality_metrics.json. Por
// eso una edición de Settings se refleja en la siguiente lectura, sin
// volver a correr el pipeline.

type Direction = 'gte' | 'lte';

type MetricReading = {
  value: number;
  direction: Direction;
  offendingSamples: string[];
};

// Un check de quality.yaml solo se puede evaluar si hay un lector para él
// aquí; es el equivalente de _METRIC_COMPUTERS en quality_gate/cli.py.
const READERS: Record<string, (metrics: QualityMetrics, threshold: number) => MetricReading> = {
  min_images_per_class: (metrics, threshold) => {
    const counts = Object.values(metrics.class_imbalance.counts);
    return {
      // Igual que metrics.min_images_per_class: sin clases, el mínimo es 0.
      value: counts.length === 0 ? 0 : Math.min(...counts),
      direction: 'gte',
      // Se recalcula contra el umbral VIGENTE: `classes_below_minimum` del
      // artefacto se calculó con el que tenía quality.yaml al correr el
      // pipeline, y Settings puede haberlo cambiado desde entonces.
      offendingSamples: Object.entries(metrics.class_imbalance.counts)
        .filter(([, count]) => count < threshold)
        .map(([name]) => name),
    };
  },
  invalid_boxes_count: (metrics) => ({
    value: metrics.invalid_boxes.invalid.length,
    direction: 'lte',
    offendingSamples: metrics.invalid_boxes.invalid.map((box) => String(box.annotation_id)),
  }),
};

export type GateCheck = {
  name: string;
  value: number | null;
  threshold: number;
  direction: Direction | null;
  severity: 'warn' | 'fail';
  passed: boolean;
  /** false cuando quality.yaml declara un check para el que el pipeline aún no tiene analizador. */
  evaluated: boolean;
  offendingSamples: string[];
};

export type GateReport = {
  /** true si ningún check `fail` está en rojo. Los `warn` no cuentan. */
  passed: boolean;
  checks: GateCheck[];
  failedChecks: number;
  warnings: number;
};

function meetsThreshold(value: number, threshold: number, direction: Direction): boolean {
  return direction === 'gte' ? value >= threshold : value <= threshold;
}

export function evaluateGate(policy: QualityPolicy, metrics: QualityMetrics): GateReport {
  const checks: GateCheck[] = Object.entries(policy.checks).map(([name, check]) => {
    const reader = READERS[name];
    if (reader === undefined) {
      // Un check sin lector NO pasa en silencio: se marca como no evaluado
      // y cuenta como no pasado (mismo criterio que UnknownCheckError).
      return {
        name,
        value: null,
        threshold: check.threshold,
        direction: null,
        severity: check.severity,
        passed: false,
        evaluated: false,
        offendingSamples: [],
      };
    }
    const reading = reader(metrics, check.threshold);
    const passed = meetsThreshold(reading.value, check.threshold, reading.direction);
    return {
      name,
      value: reading.value,
      threshold: check.threshold,
      direction: reading.direction,
      severity: check.severity,
      passed,
      evaluated: true,
      offendingSamples: passed ? [] : reading.offendingSamples,
    };
  });

  const blocking = checks.filter((check) => !check.passed && check.severity === 'fail');
  return {
    passed: blocking.length === 0,
    checks,
    failedChecks: checks.filter((check) => !check.passed).length,
    warnings: checks.filter((check) => !check.passed && check.severity === 'warn').length,
  };
}
