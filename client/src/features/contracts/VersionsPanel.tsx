import type { ReleaseDiff, VersionsReport } from './schemas';

function IdList({ label, ids }: { label: string; ids: number[] }) {
  return (
    <div className="contracts__diff-row">
      <span className="contracts__diff-label">
        {label} ({ids.length})
      </span>
      {ids.length === 0 ? (
        <span className="contracts__muted">—</span>
      ) : (
        <ul className="contracts__chips">
          {ids.map((id) => (
            <li key={id} className="contracts__chip contracts__chip--mono">
              {id}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function DiffBlock({ diff }: { diff: ReleaseDiff }) {
  const belowMinimum = new Set(diff.classes_below_minimum);

  return (
    <div className="contracts__diff">
      <p className="contracts__diff-title">
        Diff {diff.from} → {diff.to}
      </p>
      <IdList label="Imágenes agregadas" ids={diff.images_added} />
      <IdList label="Imágenes eliminadas" ids={diff.images_removed} />
      <IdList label="Cajas agregadas" ids={diff.boxes_added} />
      <IdList label="Cajas eliminadas" ids={diff.boxes_removed} />

      <div className="contracts__diff-row">
        <span className="contracts__diff-label">Imágenes por clase</span>
        <ul className="contracts__chips">
          {Object.entries(diff.images_per_class).map(([className, total]) => (
            <li
              key={className}
              // Una clase bajo el mínimo se marca aquí mismo: es el dato que
              // explica por qué la compuerta de calidad bloquea.
              className={`contracts__chip${belowMinimum.has(className) ? ' contracts__chip--alert' : ''}`}
              data-testid={`release-class-${className}`}
            >
              {className}: {total}
              {belowMinimum.has(className) ? ' ⚠' : ''}
            </li>
          ))}
        </ul>
      </div>

      <div className="contracts__diff-row">
        <span className="contracts__diff-label">
          Clases bajo el mínimo ({diff.classes_below_minimum.length})
        </span>
        {diff.classes_below_minimum.length === 0 ? (
          <span className="contracts__muted">ninguna</span>
        ) : (
          <ul className="contracts__chips">
            {diff.classes_below_minimum.map((className) => (
              <li key={className} className="contracts__chip contracts__chip--alert">
                {className}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

export function VersionsPanel({ report }: { report: VersionsReport }) {
  // El contrato lista los releases del más viejo al más nuevo; se invierte
  // una copia (no el arreglo original) para leer el historial como un
  // timeline, con el más reciente arriba.
  const releases = [...report.releases].reverse();

  return (
    <section className="contracts__panel" aria-label="Versiones del dataset">
      <header className="contracts__panel-header">
        <h3 className="contracts__panel-title">Versiones · versions.json</h3>
        <span className="contracts__badge contracts__badge--neutral" data-testid="versions-current">
          versión actual {report.current}
        </span>
      </header>

      <ol className="contracts__releases">
        {releases.map((release) => (
          <li
            key={release.version}
            className="contracts__release"
            data-testid={`release-${release.version}`}
          >
            <div className="contracts__release-header">
              <span className="contracts__release-version">{release.version}</span>
              {release.version === report.current && (
                <span className="contracts__badge contracts__badge--ok">actual</span>
              )}
              <span className="contracts__release-meta">{release.created_at}</span>
              <span className="contracts__release-meta">dvc_rev {release.dvc_rev}</span>
            </div>
            <p className="contracts__release-message">{release.message}</p>
            {release.diff_vs_previous === null ? (
              <p className="contracts__muted">Sin diff: es el primer release del dataset.</p>
            ) : (
              <DiffBlock diff={release.diff_vs_previous} />
            )}
          </li>
        ))}
      </ol>
    </section>
  );
}
