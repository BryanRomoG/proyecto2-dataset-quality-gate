import type { CSSProperties } from 'react';
import type { QualityMetrics, QualityMetricsResult } from '../../api/telemetry';

function formatPercent(value: number): string {
  return `${value.toFixed(1)}%`;
}

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function Metric({
  label,
  value,
  color,
  testId,
}: {
  label: string;
  value: string;
  color: string;
  testId: string;
}) {
  return (
    <div className="dashboard__metric" style={{ '--metric-color': color } as CSSProperties}>
      <span className="dashboard__metric-label">{label}</span>
      <span className="dashboard__metric-value" data-testid={testId}>
        {value}
      </span>
    </div>
  );
}

function SmallObjectsPanel({ report }: { report: QualityMetrics['small_objects'] }) {
  return (
    <div className="dashboard__panel">
      <h4 className="dashboard__section-title">
        Objetos pequeños · umbral {report.threshold_px}px
      </h4>
      <div className="dashboard__metrics">
        <Metric
          label="% bajo el umbral"
          value={formatPercent(report.percentage_below_threshold)}
          color="#f4a261"
          testId="telemetry-small-percentage"
        />
        <Metric
          label="Objetos pequeños"
          value={`${report.small_count} / ${report.total_annotations}`}
          color="#3fa9f5"
          testId="telemetry-small-count"
        />
        <Metric
          label="Clase más afectada"
          value={report.most_affected_category ?? '—'}
          color="#a78bfa"
          testId="telemetry-small-most-affected"
        />
      </div>
      {report.offending_sample_ids.length > 0 && (
        <p className="dashboard__muted">
          Muestras: {report.offending_sample_ids.join(', ')}
          {report.small_count > report.offending_sample_ids.length ? ' …' : ''}
        </p>
      )}
    </div>
  );
}

function ClassImbalancePanel({ report }: { report: QualityMetrics['class_imbalance'] }) {
  const belowMinimum = new Set(report.classes_below_minimum);
  const classes = Object.entries(report.counts).sort(([, a], [, b]) => b - a);
  const maxCount = classes.reduce((max, [, count]) => Math.max(max, count), 0);

  return (
    <div className="dashboard__panel">
      <h4 className="dashboard__section-title">Desbalance de clases</h4>
      <div className="dashboard__metrics">
        <Metric
          label="Ratio mayoría/minoría"
          // null cuando alguna clase está en 0: el ratio no existe, y
          // mostrar "0" o "∞" sería inventarlo.
          value={
            report.majority_minority_ratio === null
              ? 'n/a (clase en 0)'
              : `${report.majority_minority_ratio.toFixed(2)}x`
          }
          color="#2dd4a7"
          testId="telemetry-imbalance-ratio"
        />
        <Metric
          label="Clases bajo el mínimo"
          value={String(report.classes_below_minimum.length)}
          color={report.classes_below_minimum.length > 0 ? '#e5484d' : '#2dd4a7'}
          testId="telemetry-below-minimum-count"
        />
      </div>
      <ul className="dashboard__bars">
        {classes.map(([className, imageCount]) => (
          <li
            key={className}
            className="dashboard__bar-row"
            data-testid={`telemetry-class-${className}`}
          >
            <span className="dashboard__bar-label">{className}</span>
            <span className="dashboard__bar-track">
              <span
                className={`dashboard__bar-fill${belowMinimum.has(className) ? ' dashboard__bar-fill--alert' : ''}`}
                style={{ width: maxCount === 0 ? '0%' : `${(imageCount / maxCount) * 100}%` }}
              />
            </span>
            <span className="dashboard__bar-value">{imageCount}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function InvalidBoxesPanel({ report }: { report: QualityMetrics['invalid_boxes'] }) {
  // Se agrupa por razón: 40 cajas con el mismo problema son un patrón, no
  // 40 incidentes sueltos.
  const countByReason = new Map<string, number>();
  for (const box of report.invalid) {
    for (const reason of box.reasons) {
      countByReason.set(reason, (countByReason.get(reason) ?? 0) + 1);
    }
  }

  return (
    <div className="dashboard__panel">
      <h4 className="dashboard__section-title">Cajas inválidas</h4>
      <div className="dashboard__metrics">
        <Metric
          label="Cajas inválidas"
          value={`${report.invalid.length} / ${report.total_annotations}`}
          color={report.invalid.length > 0 ? '#e5484d' : '#2dd4a7'}
          testId="telemetry-invalid-count"
        />
      </div>
      {countByReason.size === 0 ? (
        <p className="dashboard__muted">Ninguna caja degenerada ni fuera de los límites.</p>
      ) : (
        <ul className="dashboard__reasons">
          {[...countByReason.entries()].map(([reason, total]) => (
            <li key={reason} data-testid={`telemetry-reason-${reason}`}>
              <code>{reason}</code>: {total}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function SpatialBiasPanel({ report }: { report: QualityMetrics['spatial_bias'] }) {
  return (
    <div className="dashboard__panel">
      <h4 className="dashboard__section-title">Sesgo espacial · área de las cajas (px²)</h4>
      <div className="dashboard__metrics">
        <Metric
          label="Media"
          value={formatNumber(report.mean)}
          color="#3fa9f5"
          testId="telemetry-spatial-mean"
        />
        <Metric
          label="Mediana"
          value={formatNumber(report.median)}
          color="#2dd4a7"
          testId="telemetry-spatial-median"
        />
        <Metric
          label="Cajas medidas"
          value={String(report.count)}
          color="#8b8f98"
          testId="telemetry-spatial-count"
        />
      </div>
      {/* Percentiles al lado de la media: si media y mediana divergen, la
          distribución está sesgada y eso tiene que verse aquí, no esconderse
          detrás de un solo número. */}
      <p className="dashboard__muted">
        p10 {formatNumber(report.p10)} · p25 {formatNumber(report.p25)} · p75{' '}
        {formatNumber(report.p75)} · p90 {formatNumber(report.p90)}
      </p>
    </div>
  );
}

function DuplicatesPanel({ report }: { report: QualityMetrics['duplicates'] }) {
  return (
    <div className="dashboard__panel">
      <h4 className="dashboard__section-title">
        Duplicados por pHash · distancia ≤ {report.distance_threshold}
      </h4>
      <div className="dashboard__metrics">
        <Metric
          label="Pares detectados"
          value={String(report.pairs.length)}
          color={report.pairs.length > 0 ? '#f4a261' : '#2dd4a7'}
          testId="telemetry-duplicates-count"
        />
      </div>
      {report.pairs.length > 0 && (
        <ul className="dashboard__reasons">
          {report.pairs.slice(0, 10).map((pair) => (
            <li key={`${pair.image_id_a}-${pair.image_id_b}`}>
              <code>
                {pair.image_id_a} ↔ {pair.image_id_b}
              </code>
              : distancia {pair.hash_distance} ({formatPercent(pair.similarity * 100)} similares)
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function PipelineTelemetry({ result }: { result: QualityMetricsResult }) {
  if (!result.available) {
    return (
      <section className="dashboard__panel" aria-label="Telemetría del pipeline">
        <h3 className="dashboard__section-title">Telemetría del pipeline (T-202)</h3>
        <p className="dashboard__hint" data-testid="telemetry-unavailable">
          {result.message} Se esperaba <code>{result.expectedPath}</code>. {result.hint}
        </p>
      </section>
    );
  }

  const { metrics } = result;

  return (
    <section className="dashboard__telemetry" aria-label="Telemetría del pipeline">
      <div className="dashboard__panel-header">
        <h3 className="dashboard__section-title">Telemetría del pipeline (T-202)</h3>
        <span className="dashboard__source" data-testid="telemetry-source">
          {result.source} · generado {result.generatedAt}
        </span>
      </div>
      <SmallObjectsPanel report={metrics.small_objects} />
      <ClassImbalancePanel report={metrics.class_imbalance} />
      <InvalidBoxesPanel report={metrics.invalid_boxes} />
      <SpatialBiasPanel report={metrics.spatial_bias} />
      <DuplicatesPanel report={metrics.duplicates} />
    </section>
  );
}
