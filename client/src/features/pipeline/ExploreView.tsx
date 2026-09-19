import { type CSSProperties, useMemo, useState } from 'react';
import {
  type EmbeddingData,
  type EmbeddingPoint,
  fetchEmbedding,
  imageUrl,
} from '../../api/pipeline';
import { ArtifactView } from './ArtifactView';

// Sección 7.6: analítica exploratoria. La proyección PCA la calcula el
// pipeline offline (etapa `embed` de DVC); aquí solo se dibuja. Filtrar por
// clase u ocultar splits es estado del cliente: no hay una sola petición al
// servidor mientras se explora, y el hover solo pide la imagen del punto.

const WIDTH = 640;
const HEIGHT = 440;
const PAD = 24;
const PALETTE = ['#3fa9f5', '#f4a261', '#2dd4a7', '#a78bfa', '#e5484d', '#e9c46a'];
const MULTI_COLOR = '#d0d3d8';
const NO_CLASS_COLOR = '#565b64';
const SPLIT_COLOR: Record<string, string> = {
  train: '#3fa9f5',
  val: '#2dd4a7',
  test: '#f4a261',
};

type ColorBy = 'class' | 'split';

function extent(values: number[]): [number, number] {
  if (values.length === 0) return [0, 1];
  const min = Math.min(...values);
  const max = Math.max(...values);
  // Rango cero (todos los puntos iguales) dividiría entre 0 al escalar.
  return min === max ? [min - 1, max + 1] : [min, max];
}

function Explorer({ data }: { data: EmbeddingData }) {
  const { points, method, explained_variance: variance } = data.embedding;

  const classes = useMemo(
    () => [...new Set(points.flatMap((point) => point.categories))].sort(),
    [points],
  );
  const classColor = useMemo(
    () => new Map(classes.map((name, index) => [name, PALETTE[index % PALETTE.length] as string])),
    [classes],
  );

  const [activeClasses, setActiveClasses] = useState<Set<string>>(() => new Set(classes));
  const [colorBy, setColorBy] = useState<ColorBy>('class');
  const [hovered, setHovered] = useState<EmbeddingPoint | null>(null);

  const [minX, maxX] = extent(points.map((point) => point.x));
  const [minY, maxY] = extent(points.map((point) => point.y));
  const scaleX = (x: number) => PAD + ((x - minX) / (maxX - minX)) * (WIDTH - 2 * PAD);
  // El eje Y del SVG crece hacia abajo; se invierte para que "arriba" sea mayor.
  const scaleY = (y: number) => HEIGHT - PAD - ((y - minY) / (maxY - minY)) * (HEIGHT - 2 * PAD);

  const visible = points.filter(
    (point) =>
      point.categories.length === 0 ||
      point.categories.some((category) => activeClasses.has(category)),
  );

  function toggleClass(name: string) {
    setActiveClasses((current) => {
      const next = new Set(current);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  }

  function colorOf(point: EmbeddingPoint): string {
    if (colorBy === 'split') return SPLIT_COLOR[point.split ?? ''] ?? NO_CLASS_COLOR;
    if (point.categories.length === 0) return NO_CLASS_COLOR;
    if (point.categories.length > 1) return MULTI_COLOR;
    return classColor.get(point.categories[0] as string) ?? NO_CLASS_COLOR;
  }

  if (points.length === 0) {
    return (
      <p className="dashboard__hint">
        La proyección no tiene puntos: ninguna imagen del COCO estaba materializada cuando se
        calculó.
      </p>
    );
  }

  return (
    <>
      <span className="dashboard__source" data-testid="explore-source">
        {data.source} · método {method.toUpperCase()}
        {variance && variance.length >= 2 && (
          <>
            {' '}
            · varianza explicada PC1 {((variance[0] as number) * 100).toFixed(1)}% · PC2{' '}
            {((variance[1] as number) * 100).toFixed(1)}%
          </>
        )}
      </span>

      <div className="pipeline__filters">
        <span className="dashboard__muted">Clases:</span>
        {classes.map((name) => (
          <button
            type="button"
            key={name}
            className="pipeline__chip"
            aria-pressed={activeClasses.has(name)}
            style={{ '--chip-color': classColor.get(name) } as CSSProperties}
            onClick={() => toggleClass(name)}
          >
            {name}
          </button>
        ))}
        <span className="dashboard__muted">Color:</span>
        {(['class', 'split'] as const).map((mode) => (
          <button
            type="button"
            key={mode}
            className="pipeline__chip"
            aria-pressed={colorBy === mode}
            onClick={() => setColorBy(mode)}
          >
            por {mode === 'class' ? 'clase' : 'split'}
          </button>
        ))}
        <span className="dashboard__source" data-testid="visible-count">
          {visible.length} de {points.length} imágenes
        </span>
      </div>

      <div className="pipeline__scatter-wrap">
        <svg
          className="pipeline__scatter"
          viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
          role="img"
          aria-label="Proyección 2D de las imágenes del dataset"
        >
          {visible.map((point) => (
            <circle
              key={point.image_id}
              data-testid="scatter-point"
              cx={scaleX(point.x)}
              cy={scaleY(point.y)}
              r={hovered?.image_id === point.image_id ? 7 : 4}
              fill={colorOf(point)}
              fillOpacity={0.85}
              stroke={hovered?.image_id === point.image_id ? '#fff' : 'none'}
              tabIndex={0}
              aria-label={`${point.file_name}: ${point.categories.join(', ') || 'sin clases'}`}
              onMouseEnter={() => setHovered(point)}
              onFocus={() => setHovered(point)}
            />
          ))}
        </svg>

        <aside className="pipeline__preview" aria-live="polite" data-testid="scatter-preview">
          {hovered ? (
            <>
              <img
                src={imageUrl(hovered.file_name)}
                alt={hovered.file_name}
                style={{
                  width: '100%',
                  maxHeight: 200,
                  objectFit: 'contain',
                  background: '#0d0e10',
                }}
              />
              <strong>{hovered.file_name}</strong>
              <span>Clases: {hovered.categories.join(', ') || 'ninguna'}</span>
              {hovered.split && <span>Split: {hovered.split}</span>}
            </>
          ) : (
            <span className="dashboard__muted">
              Pasa el cursor sobre un punto para ver la imagen.
            </span>
          )}
        </aside>
      </div>
    </>
  );
}

export function ExploreView() {
  return (
    <ArtifactView label="Explorar" title="Explorar" fetcher={fetchEmbedding} pollMs={3_600_000}>
      {(data) => <Explorer data={data} />}
    </ArtifactView>
  );
}
