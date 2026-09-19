import { useState } from 'react';
import { type Release, type RemoteStatus, fetchVersions } from '../../api/pipeline';
import { ArtifactView } from './ArtifactView';

// Sección 7.4: línea de tiempo de releases, estado DEV / PROD de cada una y
// diff entre dos versiones cualesquiera (no solo vecinas).

const REMOTE_LABEL: Record<RemoteStatus, { text: string; tone: string }> = {
  in_sync: { text: 'en sync', tone: 'ok' },
  missing: { text: 'falta', tone: 'fail' },
  unknown: { text: 'sin verificar', tone: 'muted' },
};

function RemoteBadge({ name, status }: { name: string; status: RemoteStatus }) {
  const label = REMOTE_LABEL[status];
  return (
    <span
      className={`pipeline__badge pipeline__badge--${label.tone}`}
      data-testid={`remote-${name}`}
    >
      {name.toUpperCase()} · {label.text}
    </span>
  );
}

function signed(value: number, digits = 0): string {
  const text = value.toFixed(digits);
  return value > 0 ? `+${text}` : text;
}

function Comparison({ from, to }: { from: Release; to: Release }) {
  const before = from.snapshot;
  const after = to.snapshot;

  if (before === null || after === null) {
    return (
      <p className="dashboard__muted" data-testid="compare-unavailable">
        No hay datos de {before === null ? from.version : to.version} para comparar: el dataset de
        esa versión no se pudo leer del remote cuando se generó versions.json.
      </p>
    );
  }

  const classes = [
    ...new Set([...Object.keys(before.images_per_class), ...Object.keys(after.images_per_class)]),
  ].sort();
  // "Salió del mínimo": cumplía en `from` y ya no en `to`. Una clase que ya
  // estaba bajo el mínimo antes no es una salida nueva.
  const leftMinimum = after.classes_below_minimum.filter(
    (name) => !before.classes_below_minimum.includes(name),
  );

  return (
    <table className="pipeline__table" data-testid="compare-table">
      <thead>
        <tr>
          <th>Métrica</th>
          <th className="pipeline__num">{from.version}</th>
          <th className="pipeline__num">{to.version}</th>
          <th className="pipeline__num">Cambio</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td>Imágenes</td>
          <td className="pipeline__num">{before.images}</td>
          <td className="pipeline__num">{after.images}</td>
          <td className="pipeline__num" data-testid="compare-images">
            {signed(after.images - before.images)}
          </td>
        </tr>
        <tr>
          <td>Cajas</td>
          <td className="pipeline__num">{before.boxes}</td>
          <td className="pipeline__num">{after.boxes}</td>
          <td className="pipeline__num" data-testid="compare-boxes">
            {signed(after.boxes - before.boxes)}
          </td>
        </tr>
        {classes.map((name) => {
          const a = before.images_per_class[name] ?? 0;
          const b = after.images_per_class[name] ?? 0;
          return (
            <tr key={name}>
              <td>Imágenes de {name}</td>
              <td className="pipeline__num">{a}</td>
              <td className="pipeline__num">{b}</td>
              <td className="pipeline__num" data-testid={`compare-class-${name}`}>
                {signed(b - a)}
              </td>
            </tr>
          );
        })}
        <tr>
          <td>% objetos pequeños</td>
          <td className="pipeline__num">{before.small_objects_pct.toFixed(2)}%</td>
          <td className="pipeline__num">{after.small_objects_pct.toFixed(2)}%</td>
          <td className="pipeline__num" data-testid="compare-small">
            {signed(after.small_objects_pct - before.small_objects_pct, 2)} pp
          </td>
        </tr>
        <tr>
          <td>Clases que salen del mínimo</td>
          <td colSpan={3} data-testid="compare-left-minimum">
            {leftMinimum.length === 0 ? 'ninguna' : leftMinimum.join(', ')}
          </td>
        </tr>
      </tbody>
    </table>
  );
}

function Versions({ releases, current }: { releases: Release[]; current: string | null }) {
  const [fromVersion, setFromVersion] = useState(
    releases[Math.max(releases.length - 2, 0)]?.version,
  );
  const [toVersion, setToVersion] = useState(releases[releases.length - 1]?.version);

  if (releases.length === 0) {
    return <p className="dashboard__hint">Todavía no hay releases con tag semver (vX.Y.Z).</p>;
  }

  const from = releases.find((release) => release.version === fromVersion);
  const to = releases.find((release) => release.version === toVersion);

  return (
    <>
      <ol className="pipeline__timeline" aria-label="Línea de tiempo de versiones">
        {[...releases].reverse().map((release) => (
          <li
            key={release.version}
            className="pipeline__release"
            data-testid={`release-${release.version}`}
          >
            <div className="pipeline__release-head">
              <span className="pipeline__release-version">{release.version}</span>
              {release.version === current && (
                <span className="pipeline__badge pipeline__badge--ok">actual</span>
              )}
              <RemoteBadge name="dev" status={release.remotes.dev} />
              <RemoteBadge name="prod" status={release.remotes.prod} />
            </div>
            <p className="dashboard__muted">
              {release.message} · {release.created_at.slice(0, 10)} · commit{' '}
              <code>{release.commit}</code>
              {release.dataset_md5 && (
                <>
                  {' '}
                  · md5 <code>{release.dataset_md5.slice(0, 8)}…</code>
                </>
              )}
            </p>
            {release.diff_vs_previous ? (
              <p className="dashboard__muted" data-testid={`diff-${release.version}`}>
                vs {release.diff_vs_previous.from}: {signed(release.diff_vs_previous.images_added)}{' '}
                imágenes / −{release.diff_vs_previous.images_removed} · +
                {release.diff_vs_previous.boxes_added} cajas / −
                {release.diff_vs_previous.boxes_removed}
                {release.diff_vs_previous.classes_left_minimum.length > 0 &&
                  ` · salen del mínimo: ${release.diff_vs_previous.classes_left_minimum.join(', ')}`}
              </p>
            ) : (
              <p className="dashboard__muted">Sin versión anterior con datos para comparar.</p>
            )}
          </li>
        ))}
      </ol>

      <div className="dashboard__panel">
        <h3 className="dashboard__section-title">Comparar dos versiones</h3>
        <div className="pipeline__compare">
          <label>
            Desde{' '}
            <select value={fromVersion} onChange={(event) => setFromVersion(event.target.value)}>
              {releases.map((release) => (
                <option key={release.version} value={release.version}>
                  {release.version}
                </option>
              ))}
            </select>
          </label>
          <label>
            Hasta{' '}
            <select value={toVersion} onChange={(event) => setToVersion(event.target.value)}>
              {releases.map((release) => (
                <option key={release.version} value={release.version}>
                  {release.version}
                </option>
              ))}
            </select>
          </label>
        </div>
        {from && to && <Comparison from={from} to={to} />}
      </div>
    </>
  );
}

export function VersionsView() {
  return (
    <ArtifactView label="Versions" title="Versions" fetcher={fetchVersions}>
      {(data) => <Versions releases={data.versions.releases} current={data.versions.current} />}
    </ArtifactView>
  );
}
