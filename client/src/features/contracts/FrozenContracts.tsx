import { useEffect, useState } from 'react';
import {
  type Quality,
  type Splits,
  type Versions,
  fetchQuality,
  fetchSplits,
  fetchVersions,
} from '../../api/contracts';
import './frozenContracts.css';

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | { status: 'ready'; quality: Quality; splits: Splits; versions: Versions };

function formatDate(iso: string): string {
  return new Date(iso).toLocaleString('es', {
    dateStyle: 'medium',
    timeStyle: 'short',
  });
}

function formatPercent(ratio: number): string {
  return `${Math.round(ratio * 100)}%`;
}

export function FrozenContracts() {
  const [state, setState] = useState<State>({ status: 'loading' });

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setState({ status: 'loading' });
      try {
        const [quality, splits, versions] = await Promise.all([
          fetchQuality(),
          fetchSplits(),
          fetchVersions(),
        ]);
        if (!cancelled) {
          setState({ status: 'ready', quality, splits, versions });
        }
      } catch (error) {
        if (!cancelled) {
          setState({ status: 'error', message: (error as Error).message });
        }
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === 'loading') {
    return (
      <section aria-label="Contratos Congelados" className="contracts">
        <output className="contracts__hint">Cargando contratos congelados...</output>
      </section>
    );
  }

  if (state.status === 'error') {
    return (
      <section aria-label="Contratos Congelados" className="contracts">
        <p role="alert" className="contracts__error">
          No se pudieron cargar los contratos congelados: {state.message}
        </p>
      </section>
    );
  }

  const { quality, splits, versions } = state;

  return (
    <section aria-label="Contratos Congelados" className="contracts">
      <h2 className="contracts__title">Contratos Congelados</h2>
      <p className="contracts__subtitle">
        Vista de los 3 contratos congelados por el equipo de datos (quality.json, splits.json,
        versions.json). Son ejemplos fijos de referencia, todavía no telemetría en vivo.
      </p>

      <div className="contracts__panel">
        <h3 className="contracts__section-title">Versiones del dataset</h3>
        <p className="contracts__current-version" data-testid="versions-current">
          Versión actual: <strong>{versions.current}</strong>
        </p>
        <ul className="contracts__release-list">
          {versions.releases.map((release) => (
            <li key={release.version} className="contracts__release">
              <div className="contracts__release-header">
                <span className="contracts__release-version">{release.version}</span>
                <span className="contracts__release-date">{formatDate(release.created_at)}</span>
                <span className="contracts__release-rev">{release.dvc_rev}</span>
              </div>
              <p className="contracts__release-message">{release.message}</p>
              {release.diff_vs_previous && (
                <div className="contracts__diff">
                  <p className="contracts__diff-line">
                    {release.diff_vs_previous.from} → {release.diff_vs_previous.to} ·{' '}
                    {release.diff_vs_previous.images_added.length} imágenes añadidas,{' '}
                    {release.diff_vs_previous.images_removed.length} eliminadas ·{' '}
                    {release.diff_vs_previous.boxes_added.length} boxes añadidos,{' '}
                    {release.diff_vs_previous.boxes_removed.length} eliminados
                  </p>
                  {release.diff_vs_previous.classes_below_minimum.length > 0 && (
                    <p className="contracts__diff-warning">
                      Clases bajo el mínimo:{' '}
                      {release.diff_vs_previous.classes_below_minimum.join(', ')}
                    </p>
                  )}
                </div>
              )}
            </li>
          ))}
        </ul>
      </div>

      <div className="contracts__panel">
        <h3 className="contracts__section-title">Quality Gate</h3>
        <p
          className={`contracts__gate-badge ${quality.passed ? 'contracts__gate-badge--pass' : 'contracts__gate-badge--fail'}`}
          data-testid="quality-gate-status"
        >
          {quality.passed ? 'PASA' : 'NO PASA'}
        </p>
        <table className="contracts__table">
          <thead>
            <tr>
              <th>Chequeo</th>
              <th>Valor</th>
              <th>Umbral</th>
              <th>Severidad</th>
              <th>Resultado</th>
              <th>Muestras</th>
            </tr>
          </thead>
          <tbody>
            {quality.checks.map((check) => (
              <tr key={check.name}>
                <td>{check.name}</td>
                <td>{check.value}</td>
                <td>
                  {check.direction} {check.threshold}
                </td>
                <td>{check.severity}</td>
                <td className={check.passed ? 'contracts__pass' : 'contracts__fail'}>
                  {check.passed ? 'OK' : 'Falla'}
                </td>
                <td>{check.offending_samples.join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="contracts__panel">
        <h3 className="contracts__section-title">Splits</h3>
        <div className="contracts__splits-summary">
          <span>Seed: {splits.seed}</span>
          <span>
            Train {formatPercent(splits.ratios.train)} ({splits.counts.train}) · Val{' '}
            {formatPercent(splits.ratios.val)} ({splits.counts.val}) · Test{' '}
            {formatPercent(splits.ratios.test)} ({splits.counts.test})
          </span>
        </div>
        <table className="contracts__table">
          <thead>
            <tr>
              <th>Imagen</th>
              <th>Split</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(splits.assignments).map(([imageId, split]) => (
              <tr key={imageId}>
                <td>{imageId}</td>
                <td>{split}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
