import { useState } from 'react';
import { Bar, BarChart, Cell, Tooltip, XAxis, YAxis } from 'recharts';
import {
  type AnalyzersData,
  type AnnotationSample,
  fetchAnalyzers,
  imageUrl,
} from '../../api/pipeline';
import { ArtifactView, BoxThumb, Metric } from './ArtifactView';

// Sección 7.2: las cinco pestañas de analizadores. Cada una muestra la salida
// real de su analizador (quality_metrics.json) con una gráfica y, cuando el
// analizador nombra muestras ofensoras, una lista que se puede abrir y
// recorrer (imagen + caja) en vez de una fila de ids sueltos.

type TabId = 'small' | 'imbalance' | 'duplicates' | 'invalid' | 'spatial';

const TABS: { id: TabId; label: string }[] = [
  { id: 'small', label: 'Objetos pequeños' },
  { id: 'imbalance', label: 'Desbalance' },
  { id: 'duplicates', label: 'Duplicados' },
  { id: 'invalid', label: 'Cajas inválidas' },
  { id: 'spatial', label: 'Sesgo espacial' },
];

const AXIS = { stroke: '#3d434c' };
const TICK = { fill: '#8b8f98', fontSize: 12 };
const TOOLTIP_STYLE = { background: '#1c1f24', border: '1px solid #3d434c', color: '#e7e5e0' };

function format(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

function SampleBrowser({ samples, empty }: { samples: AnnotationSample[]; empty: string }) {
  const [selected, setSelected] = useState(0);

  if (samples.length === 0) {
    return <p className="dashboard__muted">{empty}</p>;
  }

  const index = Math.min(selected, samples.length - 1);
  const current = samples[index] as AnnotationSample;

  return (
    <div className="pipeline__detail" data-testid="sample-browser">
      <div>
        <BoxThumb
          fileName={current.fileName}
          width={current.width}
          height={current.height}
          bbox={current.bbox}
          src={imageUrl(current.fileName)}
        />
        <p className="dashboard__muted" data-testid="sample-detail">
          Anotación {current.annotationId} · {current.category} · {current.fileName} · caja [
          {current.bbox.map(format).join(', ')}]
          {current.reasons.length > 0 && ` · ${current.reasons.join(', ')}`}
        </p>
        <div className="dashboard__live">
          <button
            type="button"
            className="dashboard__refresh"
            disabled={index === 0}
            onClick={() => setSelected(index - 1)}
          >
            Anterior
          </button>
          <span className="dashboard__source">
            {index + 1} / {samples.length}
          </span>
          <button
            type="button"
            className="dashboard__refresh"
            disabled={index === samples.length - 1}
            onClick={() => setSelected(index + 1)}
          >
            Siguiente
          </button>
        </div>
      </div>
      <div className="pipeline__grid">
        {samples.map((sample, position) => (
          <button
            type="button"
            key={sample.annotationId}
            className="pipeline__sample"
            aria-pressed={position === index}
            onClick={() => setSelected(position)}
          >
            <BoxThumb
              fileName={sample.fileName}
              width={sample.width}
              height={sample.height}
              bbox={sample.bbox}
              src={imageUrl(sample.fileName)}
            />
            <span className="pipeline__sample-meta">
              #{sample.annotationId} · {sample.category}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function SmallObjectsTab({ data }: { data: AnalyzersData }) {
  const report = data.metrics.small_objects;
  const rest = report.total_annotations - report.small_count;
  return (
    <div className="dashboard__panel">
      <h3 className="dashboard__section-title">
        Objetos pequeños · umbral {report.threshold_px}px
      </h3>
      <div className="dashboard__metrics">
        <Metric
          label="% bajo el umbral"
          value={`${report.percentage_below_threshold.toFixed(1)}%`}
          color="#f4a261"
          testId="small-percentage"
        />
        <Metric
          label="Objetos pequeños"
          value={`${report.small_count} / ${report.total_annotations}`}
          testId="small-count"
        />
        <Metric
          label="Clase más afectada"
          value={report.most_affected_category ?? '—'}
          color="#a78bfa"
          testId="small-most-affected"
        />
      </div>
      <BarChart
        width={480}
        height={120}
        layout="vertical"
        data={[{ name: 'cajas', pequeños: report.small_count, resto: rest }]}
        margin={{ top: 4, right: 16, left: 0, bottom: 4 }}
      >
        <XAxis type="number" tick={TICK} axisLine={AXIS} tickLine={false} />
        <YAxis type="category" dataKey="name" tick={TICK} axisLine={AXIS} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="pequeños" stackId="a" fill="#f4a261" />
        <Bar dataKey="resto" stackId="a" fill="#3fa9f5" />
      </BarChart>
      <SampleBrowser
        samples={data.samples.small}
        empty="Ningún objeto cae bajo el umbral: no hay muestras ofensoras."
      />
      {report.small_count > data.samples.small.length && (
        <p className="dashboard__muted">
          El analizador nombra solo las primeras {report.offending_sample_ids.length} de{' '}
          {report.small_count} muestras.
        </p>
      )}
    </div>
  );
}

function ImbalanceTab({ data }: { data: AnalyzersData }) {
  const report = data.metrics.class_imbalance;
  const below = new Set(report.classes_below_minimum);
  const rows = Object.entries(report.counts)
    .map(([name, images]) => ({ name, images }))
    .sort((a, b) => b.images - a.images);
  return (
    <div className="dashboard__panel">
      <h3 className="dashboard__section-title">Desbalance de clases · imágenes por clase</h3>
      <div className="dashboard__metrics">
        <Metric
          label="Ratio mayoría/minoría"
          value={
            report.majority_minority_ratio === null
              ? 'n/a (clase en 0)'
              : `${report.majority_minority_ratio.toFixed(2)}x`
          }
          color="#2dd4a7"
          testId="imbalance-ratio"
        />
        <Metric
          label="Clases bajo el mínimo"
          value={String(report.classes_below_minimum.length)}
          color={report.classes_below_minimum.length > 0 ? '#e5484d' : '#2dd4a7'}
          testId="imbalance-below"
        />
      </div>
      <BarChart
        width={480}
        height={240}
        data={rows}
        margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
      >
        <XAxis dataKey="name" tick={TICK} axisLine={AXIS} tickLine={false} />
        <YAxis allowDecimals={false} tick={TICK} axisLine={AXIS} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="images" name="imágenes">
          {rows.map((row) => (
            <Cell key={row.name} fill={below.has(row.name) ? '#e5484d' : '#3fa9f5'} />
          ))}
        </Bar>
      </BarChart>
      <table className="pipeline__table">
        <thead>
          <tr>
            <th>Clase</th>
            <th className="pipeline__num">Imágenes</th>
            <th>Estado</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.name} data-testid={`imbalance-row-${row.name}`}>
              <td>{row.name}</td>
              <td className="pipeline__num">{row.images}</td>
              <td>
                <span
                  className={`pipeline__badge pipeline__badge--${below.has(row.name) ? 'fail' : 'ok'}`}
                >
                  {below.has(row.name) ? 'bajo el mínimo' : 'ok'}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Con un dataset ruidoso los pares se cuentan por cientos: se muestran los de
// menor distancia (los más parecidos) y se dice cuántos quedan fuera.
const MAX_DUPLICATE_PAIRS = 24;

function DuplicatesTab({ data }: { data: AnalyzersData }) {
  const report = data.metrics.duplicates;
  const pairs = [...data.samples.duplicates]
    .sort((a, b) => a.hashDistance - b.hashDistance)
    .slice(0, MAX_DUPLICATE_PAIRS);
  return (
    <div className="dashboard__panel">
      <h3 className="dashboard__section-title">
        Duplicados por pHash · distancia ≤ {report.distance_threshold}
      </h3>
      <div className="dashboard__metrics">
        <Metric
          label="Pares detectados"
          value={String(report.pairs.length)}
          color={report.pairs.length > 0 ? '#f4a261' : '#2dd4a7'}
          testId="duplicates-count"
        />
      </div>
      {report.pairs.length > pairs.length && (
        <p className="dashboard__muted" data-testid="duplicates-truncated">
          Se muestran los {pairs.length} pares más parecidos de {report.pairs.length}.
        </p>
      )}
      {pairs.length === 0 ? (
        <p className="dashboard__muted">
          Ninguna imagen está a distancia ≤ {report.distance_threshold} de otra.
        </p>
      ) : (
        <div className="pipeline__grid">
          {pairs.map((pair) => (
            <div
              key={`${pair.a.imageId}-${pair.b.imageId}`}
              className="pipeline__sample"
              data-testid="duplicate-pair"
            >
              <BoxThumb {...pair.a} src={imageUrl(pair.a.fileName)} />
              <BoxThumb {...pair.b} src={imageUrl(pair.b.fileName)} />
              <span className="pipeline__sample-meta">
                {pair.a.fileName} ↔ {pair.b.fileName}
                <br />
                distancia {pair.hashDistance} · {(pair.similarity * 100).toFixed(1)}% similares
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function InvalidBoxesTab({ data }: { data: AnalyzersData }) {
  const report = data.metrics.invalid_boxes;
  const byReason = new Map<string, number>();
  for (const box of report.invalid) {
    for (const reason of box.reasons) {
      byReason.set(reason, (byReason.get(reason) ?? 0) + 1);
    }
  }
  const rows = [...byReason.entries()].map(([reason, boxes]) => ({ reason, boxes }));
  return (
    <div className="dashboard__panel">
      <h3 className="dashboard__section-title">Cajas inválidas / degeneradas</h3>
      <div className="dashboard__metrics">
        <Metric
          label="Cajas inválidas"
          value={`${report.invalid.length} / ${report.total_annotations}`}
          color={report.invalid.length > 0 ? '#e5484d' : '#2dd4a7'}
          testId="invalid-count"
        />
      </div>
      {rows.length > 0 && (
        <BarChart
          width={480}
          height={200}
          data={rows}
          margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
        >
          <XAxis dataKey="reason" tick={TICK} axisLine={AXIS} tickLine={false} />
          <YAxis allowDecimals={false} tick={TICK} axisLine={AXIS} tickLine={false} />
          <Tooltip contentStyle={TOOLTIP_STYLE} />
          <Bar dataKey="boxes" name="cajas" fill="#e5484d" />
        </BarChart>
      )}
      <SampleBrowser
        samples={data.samples.invalid}
        empty="Ninguna caja degenerada ni fuera de los límites."
      />
    </div>
  );
}

function SpatialBiasTab({ data }: { data: AnalyzersData }) {
  const report = data.metrics.spatial_bias;
  const rows = [
    { name: 'p10', area: report.p10, color: '#3fa9f5' },
    { name: 'p25', area: report.p25, color: '#3fa9f5' },
    { name: 'mediana', area: report.median, color: '#2dd4a7' },
    { name: 'media', area: report.mean, color: '#f4a261' },
    { name: 'p75', area: report.p75, color: '#3fa9f5' },
    { name: 'p90', area: report.p90, color: '#3fa9f5' },
  ];
  // Media muy por encima de la mediana = cola larga de cajas grandes: la
  // media sola escondería que la distribución está sesgada.
  const skew = report.median === 0 ? null : report.mean / report.median;
  return (
    <div className="dashboard__panel">
      <h3 className="dashboard__section-title">Sesgo espacial · área de las cajas (px²)</h3>
      <div className="dashboard__metrics">
        <Metric label="Media" value={format(report.mean)} color="#f4a261" testId="spatial-mean" />
        <Metric
          label="Mediana"
          value={format(report.median)}
          color="#2dd4a7"
          testId="spatial-median"
        />
        <Metric
          label="Media / mediana"
          value={skew === null ? 'n/a' : `${skew.toFixed(2)}x`}
          color="#a78bfa"
          testId="spatial-skew"
        />
        <Metric label="Cajas medidas" value={String(report.count)} color="#8b8f98" />
      </div>
      <BarChart
        width={520}
        height={260}
        data={rows}
        margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
      >
        <XAxis dataKey="name" tick={TICK} axisLine={AXIS} tickLine={false} />
        <YAxis tick={TICK} axisLine={AXIS} tickLine={false} />
        <Tooltip contentStyle={TOOLTIP_STYLE} />
        <Bar dataKey="area" name="área (px²)">
          {rows.map((row) => (
            <Cell key={row.name} fill={row.color} />
          ))}
        </Bar>
      </BarChart>
      <p className="dashboard__muted">
        Este analizador reporta la distribución del área de las cajas, sin coordenadas: no hay
        muestras ofensoras que abrir.
      </p>
    </div>
  );
}

function Analyzers({ data }: { data: AnalyzersData }) {
  const [tab, setTab] = useState<TabId>('small');
  return (
    <>
      <span className="dashboard__source" data-testid="analyzers-source">
        {data.source} · generado {data.generatedAt}
      </span>
      <div className="pipeline__tabs" role="tablist" aria-label="Analizadores">
        {TABS.map((item) => (
          <button
            type="button"
            key={item.id}
            role="tab"
            aria-selected={tab === item.id}
            className="pipeline__tab"
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <div className="dashboard__chart-scroll" role="tabpanel">
        {tab === 'small' && <SmallObjectsTab data={data} />}
        {tab === 'imbalance' && <ImbalanceTab data={data} />}
        {tab === 'duplicates' && <DuplicatesTab data={data} />}
        {tab === 'invalid' && <InvalidBoxesTab data={data} />}
        {tab === 'spatial' && <SpatialBiasTab data={data} />}
      </div>
    </>
  );
}

export function AnalyzersView() {
  return (
    <ArtifactView label="Analyzers" title="Analyzers" fetcher={fetchAnalyzers}>
      {(data) => <Analyzers data={data} />}
    </ArtifactView>
  );
}
