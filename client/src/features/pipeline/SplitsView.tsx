import { Bar, BarChart, Legend, Tooltip, XAxis, YAxis } from 'recharts';
import { type SplitKey, type SplitsData, fetchSplits } from '../../api/pipeline';
import { ArtifactView, Metric } from './ArtifactView';

// Sección 7.3: distribución de clases por split y resultado del chequeo de
// fuga. Los números salen de recontar splits.json contra el COCO y los pares
// de pHash reales; no de los `counts` que el propio split declara de sí mismo.

const SPLITS: SplitKey[] = ['train', 'val', 'test'];
const SPLIT_COLOR: Record<SplitKey, string> = {
  train: '#3fa9f5',
  val: '#2dd4a7',
  test: '#f4a261',
};
const TICK = { fill: '#8b8f98', fontSize: 12 };
const AXIS = { stroke: '#3d434c' };

function percent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function Splits({ data }: { data: SplitsData }) {
  const { report } = data;
  const total = SPLITS.reduce((sum, name) => sum + report.imagesPerSplit[name], 0);
  const { leakage } = report;

  return (
    <>
      <span className="dashboard__source" data-testid="splits-source">
        {data.source} · semilla {report.seed}
      </span>

      <div
        className={`pipeline__gate pipeline__gate--${leakage.ok ? 'ok' : 'blocked'}`}
        data-testid="leakage-result"
      >
        <span className={`pipeline__badge pipeline__badge--${leakage.ok ? 'ok' : 'fail'}`}>
          {leakage.ok ? 'SIN FUGA' : 'HAY FUGA'}
        </span>
        <span>
          {leakage.duplicatePairsChecked} par(es) de near-duplicates revisados ·{' '}
          {leakage.crossSplitPairs.length} repartido(s) entre splits
          {leakage.unassignedImages.length > 0 &&
            ` · ${leakage.unassignedImages.length} imagen(es) sin split`}
          {leakage.unknownImages.length > 0 &&
            ` · ${leakage.unknownImages.length} id(s) que no existen en el COCO`}
          {!leakage.countsConsistent && ' · los conteos de splits.json no coinciden'}
        </span>
      </div>

      {leakage.crossSplitPairs.length > 0 && (
        <table className="pipeline__table" data-testid="leaked-pairs">
          <thead>
            <tr>
              <th>Imagen A</th>
              <th>Imagen B</th>
              <th>Distancia pHash</th>
            </tr>
          </thead>
          <tbody>
            {leakage.crossSplitPairs.map((pair) => (
              <tr key={`${pair.imageIdA}-${pair.imageIdB}`}>
                <td>
                  {pair.imageIdA} ({pair.splitA})
                </td>
                <td>
                  {pair.imageIdB} ({pair.splitB})
                </td>
                <td className="pipeline__num">{pair.hashDistance}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      <div className="dashboard__metrics">
        {SPLITS.map((name) => (
          <Metric
            key={name}
            label={`${name} · ${percent(report.actualRatios[name])} (objetivo ${percent(report.ratios[name] ?? 0)})`}
            value={String(report.imagesPerSplit[name])}
            color={SPLIT_COLOR[name]}
            testId={`split-images-${name}`}
          />
        ))}
        <Metric
          label="Total de imágenes"
          value={String(total)}
          color="#8b8f98"
          testId="split-total"
        />
      </div>

      <div className="dashboard__panel">
        <h3 className="dashboard__section-title">Imágenes por clase y split</h3>
        <div className="dashboard__chart-scroll">
          <BarChart
            width={520}
            height={260}
            data={report.classes}
            margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
          >
            <XAxis dataKey="className" tick={TICK} axisLine={AXIS} tickLine={false} />
            <YAxis allowDecimals={false} tick={TICK} axisLine={AXIS} tickLine={false} />
            <Tooltip
              contentStyle={{
                background: '#1c1f24',
                border: '1px solid #3d434c',
                color: '#e7e5e0',
              }}
            />
            <Legend />
            {SPLITS.map((name) => (
              <Bar key={name} dataKey={name} stackId="split" fill={SPLIT_COLOR[name]} />
            ))}
          </BarChart>
        </div>
        <table className="pipeline__table">
          <thead>
            <tr>
              <th>Clase</th>
              {SPLITS.map((name) => (
                <th key={name} className="pipeline__num">
                  {name}
                </th>
              ))}
              <th className="pipeline__num">Total</th>
            </tr>
          </thead>
          <tbody>
            {report.classes.map((row) => (
              <tr key={row.className} data-testid={`split-class-${row.className}`}>
                <td>{row.className}</td>
                {SPLITS.map((name) => (
                  <td
                    key={name}
                    className="pipeline__num"
                    data-testid={`split-${row.className}-${name}`}
                  >
                    {row[name]}{' '}
                    <span className="dashboard__muted">
                      ({percent(row.total === 0 ? 0 : row[name] / row.total)})
                    </span>
                  </td>
                ))}
                <td className="pipeline__num">{row.total}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export function SplitsView() {
  return (
    <ArtifactView label="Splits" title="Splits" fetcher={fetchSplits}>
      {(data) => <Splits data={data} />}
    </ArtifactView>
  );
}
