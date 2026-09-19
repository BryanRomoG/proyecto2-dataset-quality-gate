import type { CSSProperties } from 'react';
import type { SplitName, SplitsReport } from './schemas';

const SPLIT_ORDER: SplitName[] = ['train', 'val', 'test'];

const SPLIT_COLOR: Record<SplitName, string> = {
  train: '#3fa9f5',
  val: '#2dd4a7',
  test: '#f4a261',
};

function toPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

export function SplitsPanel({ report }: { report: SplitsReport }) {
  const assignments = Object.entries(report.assignments);
  const totalAssigned = report.counts.train + report.counts.val + report.counts.test;

  return (
    <section className="contracts__panel" aria-label="Splits estratificados">
      <header className="contracts__panel-header">
        <h3 className="contracts__panel-title">Splits · splits.json</h3>
        <span className="contracts__badge contracts__badge--neutral" data-testid="splits-seed">
          seed {report.seed}
        </span>
      </header>

      <div className="contracts__metrics">
        {SPLIT_ORDER.map((split) => (
          <div
            key={split}
            className="contracts__metric"
            style={{ '--metric-color': SPLIT_COLOR[split] } as CSSProperties}
          >
            <span className="contracts__metric-label">
              {split} · {toPercent(report.ratios[split])} objetivo
            </span>
            <span className="contracts__metric-value" data-testid={`splits-count-${split}`}>
              {report.counts[split]}
            </span>
          </div>
        ))}
      </div>

      {/* La barra dibuja los ratios del contrato (la proporción pedida), no
          los counts: con datasets chicos los counts reales rara vez caen
          exactos en 70/15/15 y mezclarlos escondería esa diferencia. */}
      <div className="contracts__ratio-bar" aria-hidden="true">
        {SPLIT_ORDER.map((split) => (
          <div
            key={split}
            className="contracts__ratio-segment"
            style={{
              width: toPercent(report.ratios[split]),
              background: SPLIT_COLOR[split],
            }}
          />
        ))}
      </div>

      <table className="contracts__table">
        <caption className="contracts__caption">
          Asignación imagen → split ({totalAssigned} imágenes en el contrato congelado).
        </caption>
        <thead>
          <tr>
            <th scope="col">Imagen (id)</th>
            <th scope="col">Split</th>
          </tr>
        </thead>
        <tbody>
          {assignments.map(([imageId, split]) => (
            <tr key={imageId} data-testid={`splits-assignment-${imageId}`}>
              <th scope="row" className="contracts__cell-num">
                {imageId}
              </th>
              <td>
                <span
                  className="contracts__chip"
                  style={{ '--chip-color': SPLIT_COLOR[split] } as CSSProperties}
                >
                  {split}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
