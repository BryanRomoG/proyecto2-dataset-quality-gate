import type { Artifact, Gate } from '../../api/pipeline';
import type { LiveState } from '../dashboard/useLiveData';
import './pipeline.css';

// Estado de la compuerta de calidad para el Overview: si bloquea o pasa, qué
// checks están en rojo y con qué valor contra qué umbral. Los `warn` en rojo
// se listan pero no cambian el veredicto (igual que en el pipeline).

type GateState = LiveState<Artifact<Gate>>;

function describe(check: Gate['checks'][number]): string {
  if (!check.evaluated || check.value === null) return 'sin analizador todavía';
  const symbol = check.direction === 'gte' ? '≥' : '≤';
  return `${check.value} (debe ser ${symbol} ${check.threshold})`;
}

export function GateStatus({ state }: { state: GateState }) {
  if (state.status === 'loading') {
    return null;
  }

  if (state.status === 'error') {
    return (
      <output className="dashboard__hint" data-testid="gate-error">
        No se pudo evaluar la compuerta de calidad: {state.message}
      </output>
    );
  }

  const result = state.data;
  if (!result.available) {
    return (
      <output className="dashboard__hint" data-testid="gate-unavailable">
        Compuerta sin evaluar: {result.message} {result.hint}
      </output>
    );
  }

  const gate = result.data;
  const failing = gate.checks.filter((check) => !check.passed);

  return (
    <section
      aria-label="Compuerta de calidad"
      className={`pipeline__gate pipeline__gate--${gate.passed ? 'ok' : 'blocked'}`}
    >
      <span
        className={`pipeline__badge pipeline__badge--${gate.passed ? 'ok' : 'fail'}`}
        data-testid="gate-state"
      >
        {gate.passed ? 'COMPUERTA: PASA' : 'COMPUERTA: BLOQUEA'}
      </span>
      <span data-testid="gate-summary">
        {gate.checks.length} check(s) evaluados · {gate.failedChecks} en rojo
        {gate.warnings > 0 && ` (${gate.warnings} warn, no bloquean)`}
      </span>
      {failing.length > 0 && (
        <ul className="dashboard__reasons" style={{ flexBasis: '100%' }}>
          {failing.map((check) => (
            <li key={check.name} data-testid={`gate-failing-${check.name}`}>
              <span
                className={`pipeline__badge pipeline__badge--${check.severity === 'fail' ? 'fail' : 'warn'}`}
              >
                {check.severity}
              </span>{' '}
              <code>{check.name}</code>: {describe(check)}
              {check.offendingSamples.length > 0 &&
                ` · ofensoras: ${check.offendingSamples.slice(0, 5).join(', ')}${check.offendingSamples.length > 5 ? '…' : ''}`}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
