import type { CSSProperties, ReactNode } from 'react';
import type { Artifact } from '../../api/pipeline';
import { useLiveData } from '../dashboard/useLiveData';
import '../dashboard/dashboard.css';
import './pipeline.css';

// Las pantallas de la sección 7 leen artefactos que escribe el pipeline. Este
// envoltorio resuelve una sola vez los cuatro estados que todas comparten:
// cargando, error, "el pipeline todavía no lo dejó en disco" (503, con el
// comando que falta) y datos listos.

const DEFAULT_POLL_MS = 15000;

type Props<T> = {
  /** Nombre accesible de la pantalla. */
  label: string;
  title: string;
  /** Debe ser una función estable (definida fuera del componente): `useLiveData` reinicia el poll si cambia. */
  fetcher: () => Promise<Artifact<T>>;
  /** Cada cuánto se relee. Las pantallas con formularios lo desactivan para no pisar lo que se está editando. */
  pollMs?: number;
  children: (data: T, refresh: () => void) => ReactNode;
};

export function ArtifactView<T>({
  label,
  title,
  fetcher,
  pollMs = DEFAULT_POLL_MS,
  children,
}: Props<T>) {
  const live = useLiveData(fetcher, pollMs);
  const state = live.state;

  if (state.status === 'loading') {
    return (
      <section aria-label={label} className="dashboard pipeline">
        <output className="dashboard__hint">Cargando {title.toLowerCase()}...</output>
      </section>
    );
  }

  if (state.status === 'error') {
    return (
      <section aria-label={label} className="dashboard pipeline">
        <p role="alert" className="dashboard__error">
          No se pudo cargar {title.toLowerCase()}: {state.message}
        </p>
      </section>
    );
  }

  const result = state.data;
  if (!result.available) {
    return (
      <section aria-label={label} className="dashboard pipeline">
        <h2 className="dashboard__title">{title}</h2>
        <p className="dashboard__hint" data-testid="artifact-unavailable">
          {result.message} Se esperaba <code>{result.expectedPath}</code>. {result.hint}
        </p>
        <button type="button" className="dashboard__refresh" onClick={() => void live.refresh()}>
          Reintentar
        </button>
      </section>
    );
  }

  return (
    <section aria-label={label} className="dashboard pipeline">
      <div className="dashboard__panel-header">
        <h2 className="dashboard__title">{title}</h2>
        <div className="dashboard__live">
          <span className="dashboard__source">
            Actualizado {state.updatedAt.toLocaleTimeString()}
          </span>
          <button type="button" className="dashboard__refresh" onClick={() => void live.refresh()}>
            Actualizar ahora
          </button>
        </div>
      </div>
      {state.warning !== null && (
        <output className="dashboard__warning">
          El último refresco falló ({state.warning}); se muestra la lectura anterior.
        </output>
      )}
      {children(result.data, () => void live.refresh())}
    </section>
  );
}

export function Metric({
  label,
  value,
  color = '#3fa9f5',
  testId,
}: {
  label: string;
  value: string;
  color?: string;
  testId?: string;
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

/** Miniatura de una imagen del dataset con su caja dibujada encima (coordenadas en % de la imagen). */
export function BoxThumb({
  fileName,
  width,
  height,
  bbox,
  src,
}: {
  fileName: string;
  width: number;
  height: number;
  bbox?: [number, number, number, number];
  src: string;
}) {
  const [x, y, w, h] = bbox ?? [0, 0, 0, 0];
  // Una caja degenerada (ancho 0 o negativo) se dibuja con su valor absoluto
  // mínimo visible: si no, la muestra ofensora sería justo la invisible.
  const boxWidth = Math.max(Math.abs(w), 0.5);
  const boxHeight = Math.max(Math.abs(h), 0.5);
  return (
    <span className="pipeline__thumb" style={{ aspectRatio: `${width} / ${height}` }}>
      <img src={src} alt={fileName} loading="lazy" />
      {bbox && (
        <span
          className="pipeline__thumb-box"
          data-testid="thumb-box"
          style={{
            left: `${(Math.min(x, x + w) / width) * 100}%`,
            top: `${(Math.min(y, y + h) / height) * 100}%`,
            width: `${(boxWidth / width) * 100}%`,
            height: `${(boxHeight / height) * 100}%`,
          }}
        />
      )}
    </span>
  );
}
