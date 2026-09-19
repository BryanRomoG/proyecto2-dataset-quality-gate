import type { QualityReport } from './schemas';

// Símbolo de la comparación tal como la define el contrato: el check pasa
// si valor >= umbral ("gte") o valor <= umbral ("lte").
const DIRECTION_LABEL = {
  gte: '>=',
  lte: '<=',
} as const;

const SEVERITY_LABEL = {
  fail: 'fail (bloquea)',
  warn: 'warn (no bloquea)',
} as const;

function formatNumber(value: number): string {
  return Number.isInteger(value) ? String(value) : value.toFixed(2);
}

export function QualityPanel({ report }: { report: QualityReport }) {
  return (
    <section className="contracts__panel" aria-label="Compuerta de calidad">
      <header className="contracts__panel-header">
        <h3 className="contracts__panel-title">Compuerta de calidad · quality.json</h3>
        <span
          className={`contracts__badge contracts__badge--${report.passed ? 'ok' : 'fail'}`}
          data-testid="quality-passed"
        >
          {report.passed ? 'Compuerta aprobada' : 'Compuerta bloqueada'}
        </span>
      </header>

      <table className="contracts__table">
        <caption className="contracts__caption">
          Cada check trae valor observado, umbral, dirección, severidad y muestras ofensoras — el
          contrato nunca es solo un booleano.
        </caption>
        <thead>
          <tr>
            <th scope="col">Check</th>
            <th scope="col">Valor</th>
            <th scope="col">Umbral</th>
            <th scope="col">Severidad</th>
            <th scope="col">Resultado</th>
            <th scope="col">Muestras ofensoras</th>
          </tr>
        </thead>
        <tbody>
          {report.checks.map((check) => (
            <tr key={check.name} data-testid={`quality-check-${check.name}`}>
              <th scope="row" className="contracts__cell-name">
                {check.name}
              </th>
              <td className="contracts__cell-num">{formatNumber(check.value)}</td>
              <td className="contracts__cell-num">
                {DIRECTION_LABEL[check.direction]} {formatNumber(check.threshold)}
              </td>
              <td>{SEVERITY_LABEL[check.severity]}</td>
              <td>
                <span
                  className={`contracts__badge contracts__badge--${check.passed ? 'ok' : 'fail'}`}
                >
                  {check.passed ? 'cumple' : 'no cumple'}
                </span>
              </td>
              <td>
                {check.offending_samples.length === 0 ? (
                  <span className="contracts__muted">—</span>
                ) : (
                  <ul className="contracts__chips">
                    {check.offending_samples.map((sample) => (
                      <li key={sample} className="contracts__chip">
                        {sample}
                      </li>
                    ))}
                  </ul>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
