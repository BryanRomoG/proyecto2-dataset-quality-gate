import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { AnalyzersView } from './AnalyzersView';
import { ExploreView } from './ExploreView';
import { SettingsView } from './SettingsView';
import { SplitsView } from './SplitsView';
import { VersionsView } from './VersionsView';

// Sección 7 (Analyzers, Splits, Versions, Settings, Explorar): cada pantalla
// pinta lo que devuelve /api/pipeline/*, nunca valores fijos, y explica qué
// falta cuando el pipeline todavía no dejó su artefacto.

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const unavailable = (path: string, hint: string) =>
  json({ error: 'El artefacto todavía no está materializado.', expectedPath: path, hint }, 503);

let routes: Record<string, (init?: RequestInit) => Response>;
let fetchMock: ReturnType<typeof vi.fn>;

beforeEach(() => {
  routes = {};
  fetchMock = vi.fn((url: string, init?: RequestInit) => {
    const handler = routes[url];
    return Promise.resolve(handler ? handler(init) : json({ error: 'sin handler' }, 404));
  });
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// --- Analyzers ---------------------------------------------------------------

const image = { imageId: 1, fileName: 'car-0001.jpg', width: 200, height: 100 };

const analyzers = {
  generatedAt: '2026-09-18T09:30:00.000Z',
  source: 'data/processed/quality_metrics.json',
  metrics: {
    small_objects: {
      threshold_px: 32,
      total_annotations: 120,
      small_count: 18,
      percentage_below_threshold: 15,
      most_affected_category: 'person',
      offending_sample_ids: [10, 11],
    },
    class_imbalance: {
      counts: { car: 317, person: 362 },
      majority_minority_ratio: 1.142,
      classes_below_minimum: [],
    },
    invalid_boxes: {
      total_annotations: 120,
      invalid: [
        { annotation_id: 10, reasons: ['zero_width'] },
        { annotation_id: 11, reasons: ['zero_width', 'out_of_image_bounds'] },
      ],
    },
    spatial_bias: {
      count: 120,
      mean: 14478.3,
      median: 8316,
      p10: 1638,
      p25: 3472,
      p75: 17216,
      p90: 34391,
    },
    duplicates: {
      distance_threshold: 8,
      pairs: [{ image_id_a: 1, image_id_b: 2, hash_distance: 3, similarity: 0.95 }],
    },
  },
  samples: {
    small: [
      {
        ...image,
        annotationId: 10,
        category: 'car',
        bbox: [10, 10, 12, 12],
        reasons: ['below_threshold'],
      },
      {
        ...image,
        imageId: 2,
        fileName: 'car-0002.jpg',
        annotationId: 11,
        category: 'person',
        bbox: [0, 0, 8, 8],
        reasons: ['below_threshold'],
      },
    ],
    invalid: [
      { ...image, annotationId: 10, category: 'car', bbox: [0, 0, 0, 20], reasons: ['zero_width'] },
    ],
    duplicates: [
      {
        hashDistance: 3,
        similarity: 0.95,
        a: image,
        b: { ...image, imageId: 2, fileName: 'car-0002.jpg' },
      },
    ],
  },
};

describe('AnalyzersView', () => {
  it('muestra las cinco pestañas con datos reales de cada analizador', async () => {
    routes['/api/pipeline/analyzers'] = () => json(analyzers);
    render(<AnalyzersView />);

    expect(await screen.findByTestId('small-percentage')).toHaveTextContent('15.0%');
    expect(screen.getByTestId('small-count')).toHaveTextContent('18 / 120');
    expect(screen.getAllByRole('tab')).toHaveLength(5);

    fireEvent.click(screen.getByRole('tab', { name: 'Desbalance' }));
    expect(screen.getByTestId('imbalance-ratio')).toHaveTextContent('1.14x');
    expect(screen.getByTestId('imbalance-row-car')).toHaveTextContent('317');

    fireEvent.click(screen.getByRole('tab', { name: 'Duplicados' }));
    expect(screen.getByTestId('duplicates-count')).toHaveTextContent('1');
    expect(screen.getByTestId('duplicate-pair')).toHaveTextContent('car-0001.jpg ↔ car-0002.jpg');

    fireEvent.click(screen.getByRole('tab', { name: 'Cajas inválidas' }));
    expect(screen.getByTestId('invalid-count')).toHaveTextContent('2 / 120');

    fireEvent.click(screen.getByRole('tab', { name: 'Sesgo espacial' }));
    expect(screen.getByTestId('spatial-mean')).toHaveTextContent('14478.30');
    expect(screen.getByTestId('spatial-median')).toHaveTextContent('8316');
    // Media 1.74x la mediana: la distribución está sesgada y se dice.
    expect(screen.getByTestId('spatial-skew')).toHaveTextContent('1.74x');
  });

  it('permite abrir y recorrer las muestras ofensoras (imagen + caja)', async () => {
    routes['/api/pipeline/analyzers'] = () => json(analyzers);
    render(<AnalyzersView />);

    const browser = await screen.findByTestId('sample-browser');
    expect(within(browser).getByTestId('sample-detail')).toHaveTextContent('Anotación 10');
    expect(within(browser).getAllByTestId('thumb-box').length).toBeGreaterThan(0);

    fireEvent.click(within(browser).getByRole('button', { name: 'Siguiente' }));
    expect(within(browser).getByTestId('sample-detail')).toHaveTextContent('Anotación 11');
    expect(within(browser).getByTestId('sample-detail')).toHaveTextContent('car-0002.jpg');
    expect(within(browser).getByRole('button', { name: 'Siguiente' })).toBeDisabled();
  });

  it('una caja de ancho cero se dibuja visible, no invisible', async () => {
    routes['/api/pipeline/analyzers'] = () => json(analyzers);
    render(<AnalyzersView />);
    await screen.findByTestId('small-percentage');
    fireEvent.click(screen.getByRole('tab', { name: 'Cajas inválidas' }));

    const box = within(screen.getByTestId('sample-browser')).getAllByTestId('thumb-box')[0];
    expect(Number.parseFloat((box as HTMLElement).style.width)).toBeGreaterThan(0);
  });

  it('explica qué falta cuando el pipeline todavía no dejó el artefacto', async () => {
    routes['/api/pipeline/analyzers'] = () =>
      unavailable('data/processed/quality_metrics.json', 'Corre `dvc pull`.');
    render(<AnalyzersView />);

    expect(await screen.findByTestId('artifact-unavailable')).toHaveTextContent('dvc pull');
  });

  it('cambiar el dato en la fuente cambia lo que se ve', async () => {
    routes['/api/pipeline/analyzers'] = () => json(analyzers);
    const first = render(<AnalyzersView />);
    expect(await screen.findByTestId('small-count')).toHaveTextContent('18 / 120');
    first.unmount();

    routes['/api/pipeline/analyzers'] = () =>
      json({
        ...analyzers,
        metrics: {
          ...analyzers.metrics,
          small_objects: { ...analyzers.metrics.small_objects, small_count: 99 },
        },
      });
    render(<AnalyzersView />);
    expect(await screen.findByTestId('small-count')).toHaveTextContent('99 / 120');
  });
});

// --- Splits ------------------------------------------------------------------

const splitsBody = (crossSplitPairs: unknown[] = []) => ({
  generatedAt: '2026-09-18T09:30:00.000Z',
  source: 'data/processed/splits.json',
  report: {
    seed: 42,
    ratios: { train: 0.7, val: 0.15, test: 0.15 },
    imagesPerSplit: { train: 258, val: 55, test: 56 },
    actualRatios: { train: 0.699, val: 0.149, test: 0.152 },
    classes: [
      { className: 'car', train: 222, val: 47, test: 48, total: 317 },
      { className: 'person', train: 253, val: 54, test: 55, total: 362 },
    ],
    leakage: {
      ok: crossSplitPairs.length === 0,
      duplicatePairsChecked: 0,
      crossSplitPairs,
      unassignedImages: [],
      unknownImages: [],
      countsConsistent: true,
    },
  },
});

describe('SplitsView', () => {
  it('muestra la distribución por clase y split y el resultado de la fuga', async () => {
    routes['/api/pipeline/splits'] = () => json(splitsBody());
    render(<SplitsView />);

    expect(await screen.findByTestId('split-images-train')).toHaveTextContent('258');
    expect(screen.getByTestId('split-total')).toHaveTextContent('369');
    expect(screen.getByTestId('split-car-val')).toHaveTextContent('47');
    expect(screen.getByTestId('split-person-test')).toHaveTextContent('55');
    expect(screen.getByTestId('leakage-result')).toHaveTextContent('SIN FUGA');
  });

  it('un par de duplicados repartido entre splits se marca como fuga y se lista', async () => {
    routes['/api/pipeline/splits'] = () =>
      json(
        splitsBody([{ imageIdA: 1, imageIdB: 3, splitA: 'train', splitB: 'val', hashDistance: 2 }]),
      );
    render(<SplitsView />);

    expect(await screen.findByTestId('leakage-result')).toHaveTextContent('HAY FUGA');
    expect(screen.getByTestId('leaked-pairs')).toHaveTextContent('1 (train)');
    expect(screen.getByTestId('leaked-pairs')).toHaveTextContent('3 (val)');
  });
});

// --- Versions ----------------------------------------------------------------

const snapshot = (images: number, car: number, person: number, small: number) => ({
  images,
  boxes: images * 4,
  images_per_class: { car, person },
  classes_below_minimum: [car, person].some((n) => n < 300) ? ['car'] : [],
  small_objects_pct: small,
});

const versionsBody = {
  generatedAt: '2026-09-18T09:30:00.000Z',
  source: 'data/processed/versions.json',
  versions: {
    current: 'v1.0.0',
    releases: [
      {
        version: 'v0.1.0',
        message: 'Primer lote',
        created_at: '2026-09-18T22:19:23-06:00',
        commit: '05fdca8',
        dataset_md5: 'aaaaaaaa11111111',
        snapshot: snapshot(100, 60, 70, 4),
        remotes: { dev: 'in_sync', prod: 'in_sync' },
        diff_vs_previous: null,
      },
      {
        version: 'v1.0.0',
        message: 'Release final',
        created_at: '2026-09-18T22:19:24-06:00',
        commit: 'f77700a',
        dataset_md5: 'c500a26a26fb7900',
        snapshot: snapshot(369, 317, 362, 5.05),
        remotes: { dev: 'missing', prod: 'in_sync' },
        diff_vs_previous: {
          from: 'v0.1.0',
          to: 'v1.0.0',
          images_added: 269,
          images_removed: 0,
          boxes_added: 1009,
          boxes_removed: 0,
          images_per_class: { car: 317, person: 362 },
          classes_below_minimum: [],
          classes_left_minimum: [],
          small_objects_pct_before: 4,
          small_objects_pct_after: 5.05,
        },
      },
    ],
  },
};

describe('VersionsView', () => {
  it('muestra la línea de tiempo con el estado DEV / PROD de cada versión', async () => {
    routes['/api/pipeline/versions'] = () => json(versionsBody);
    render(<VersionsView />);

    const latest = await screen.findByTestId('release-v1.0.0');
    expect(within(latest).getByTestId('remote-dev')).toHaveTextContent('DEV · falta');
    expect(within(latest).getByTestId('remote-prod')).toHaveTextContent('PROD · en sync');
    expect(latest).toHaveTextContent('actual');
    expect(screen.getByTestId('diff-v1.0.0')).toHaveTextContent('+269');

    const first = screen.getByTestId('release-v0.1.0');
    expect(first).toHaveTextContent('Sin versión anterior');
  });

  it('compara dos versiones cualesquiera restando sus fotos', async () => {
    routes['/api/pipeline/versions'] = () => json(versionsBody);
    render(<VersionsView />);

    // Por defecto compara las dos últimas: v0.1.0 -> v1.0.0.
    expect(await screen.findByTestId('compare-images')).toHaveTextContent('+269');
    expect(screen.getByTestId('compare-boxes')).toHaveTextContent('+1076');
    expect(screen.getByTestId('compare-class-car')).toHaveTextContent('+257');
    expect(screen.getByTestId('compare-small')).toHaveTextContent('+1.05 pp');
  });

  it('si una versión no tiene datos, lo dice en vez de inventar una comparación', async () => {
    const body = {
      ...versionsBody,
      versions: {
        ...versionsBody.versions,
        releases: versionsBody.versions.releases.map((release) =>
          release.version === 'v0.1.0' ? { ...release, snapshot: null } : release,
        ),
      },
    };
    routes['/api/pipeline/versions'] = () => json(body);
    render(<VersionsView />);

    expect(await screen.findByTestId('compare-unavailable')).toHaveTextContent('v0.1.0');
  });

  it('explica cómo generar versions.json si todavía no existe', async () => {
    routes['/api/pipeline/versions'] = () =>
      unavailable('data/processed/versions.json', 'Genera la línea con build_versions.py.');
    render(<VersionsView />);

    expect(await screen.findByTestId('artifact-unavailable')).toHaveTextContent(
      'build_versions.py',
    );
  });
});

// --- Settings ----------------------------------------------------------------

const policy = {
  checks: {
    min_images_per_class: { threshold: 300, severity: 'fail' },
    invalid_boxes_count: { threshold: 5, severity: 'warn' },
  },
};

describe('SettingsView', () => {
  it('carga los umbrales de quality.yaml y no permite guardar sin cambios', async () => {
    routes['/api/pipeline/settings'] = () => json({ policy });
    render(<SettingsView />);

    expect(await screen.findByLabelText('Umbral de min_images_per_class')).toHaveValue(300);
    expect(screen.getByLabelText('Severidad de invalid_boxes_count')).toHaveValue('warn');
    expect(screen.getByRole('button', { name: /Guardar/ })).toBeDisabled();
  });

  it('guarda con PUT y muestra cómo queda la compuerta con la política nueva', async () => {
    routes['/api/pipeline/settings'] = (init) => {
      if (init?.method === 'PUT') {
        const sent = JSON.parse(String(init.body));
        return json({
          policy: sent,
          gate: { passed: false, checks: [], failedChecks: 1, warnings: 0 },
        });
      }
      return json({ policy });
    };
    render(<SettingsView />);

    const input = await screen.findByLabelText('Umbral de min_images_per_class');
    fireEvent.change(input, { target: { value: '999' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar/ }));

    expect(await screen.findByTestId('save-result')).toHaveTextContent('BLOQUEA');
    const put = fetchMock.mock.calls.find(([, init]) => init?.method === 'PUT');
    expect(JSON.parse(String(put?.[1]?.body)).checks.min_images_per_class.threshold).toBe(999);
    // Tras guardar, el formulario queda limpio: lo que se ve es lo persistido.
    expect(screen.getByRole('button', { name: /Guardar/ })).toBeDisabled();
  });

  it('muestra los errores de validación del server sin dar por guardado el cambio', async () => {
    routes['/api/pipeline/settings'] = (init) =>
      init?.method === 'PUT'
        ? json(
            { error: 'inválido', issues: ['checks.min_images_per_class.threshold: negativo'] },
            422,
          )
        : json({ policy });
    render(<SettingsView />);

    const input = await screen.findByLabelText('Umbral de min_images_per_class');
    fireEvent.change(input, { target: { value: '5' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('negativo');
    expect(screen.queryByTestId('save-result')).not.toBeInTheDocument();
  });

  it('no manda un umbral vacío como si fuera 0', async () => {
    routes['/api/pipeline/settings'] = () => json({ policy });
    render(<SettingsView />);

    const input = await screen.findByLabelText('Umbral de min_images_per_class');
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.click(screen.getByRole('button', { name: /Guardar/ }));

    expect(await screen.findByRole('alert')).toHaveTextContent('debe ser un número');
    expect(fetchMock.mock.calls.some(([, init]) => init?.method === 'PUT')).toBe(false);
  });

  it('avisa (sin bloquear) cuando el umbral queda bajo el mínimo del curso', async () => {
    routes['/api/pipeline/settings'] = () => json({ policy });
    render(<SettingsView />);

    expect(await screen.findByLabelText('Umbral de min_images_per_class')).toBeInTheDocument();
    expect(screen.queryByTestId('course-warning')).not.toBeInTheDocument();

    const input = screen.getByLabelText('Umbral de min_images_per_class');
    fireEvent.change(input, { target: { value: '50' } });

    expect(screen.getByTestId('course-warning')).toHaveTextContent('300');
    expect(screen.getByRole('button', { name: /Guardar/ })).toBeEnabled();
  });
});

// --- Explorar ----------------------------------------------------------------

const embeddingBody = {
  generatedAt: '2026-09-18T09:30:00.000Z',
  source: 'data/processed/embedding.json',
  embedding: {
    method: 'pca',
    explained_variance: [0.4, 0.2],
    points: [
      { image_id: 1, file_name: 'car-1.jpg', x: 0, y: 0, categories: ['car'], split: 'train' },
      { image_id: 2, file_name: 'car-2.jpg', x: 1, y: 1, categories: ['car'], split: 'val' },
      {
        image_id: 3,
        file_name: 'person-1.jpg',
        x: -1,
        y: 1,
        categories: ['person'],
        split: 'train',
      },
      {
        image_id: 4,
        file_name: 'both-1.jpg',
        x: 2,
        y: -1,
        categories: ['car', 'person'],
        split: 'test',
      },
    ],
  },
};

describe('ExploreView', () => {
  it('filtra por clase en el cliente, sin volver a llamar al servidor', async () => {
    routes['/api/pipeline/embedding'] = () => json(embeddingBody);
    render(<ExploreView />);

    expect(await screen.findAllByTestId('scatter-point')).toHaveLength(4);
    expect(screen.getByTestId('explore-source')).toHaveTextContent('PC1 40.0%');
    const callsBefore = fetchMock.mock.calls.length;

    fireEvent.click(screen.getByRole('button', { name: 'car' }));
    // Sin "car": queda person-1 y la imagen que tiene person y car (sigue en pantalla por person).
    expect(screen.getAllByTestId('scatter-point')).toHaveLength(2);
    expect(screen.getByTestId('visible-count')).toHaveTextContent('2 de 4');

    fireEvent.click(screen.getByRole('button', { name: 'person' }));
    expect(screen.queryAllByTestId('scatter-point')).toHaveLength(0);

    fireEvent.click(screen.getByRole('button', { name: 'car' }));
    expect(screen.getAllByTestId('scatter-point')).toHaveLength(3);
    expect(fetchMock.mock.calls.length).toBe(callsBefore);
  });

  it('el hover sobre un punto muestra su imagen y datos', async () => {
    routes['/api/pipeline/embedding'] = () => json(embeddingBody);
    render(<ExploreView />);

    const points = await screen.findAllByTestId('scatter-point');
    fireEvent.mouseEnter(points[2] as Element);

    const preview = screen.getByTestId('scatter-preview');
    await waitFor(() =>
      expect(within(preview).getByRole('img')).toHaveAttribute(
        'src',
        '/api/pipeline/images/person-1.jpg',
      ),
    );
    expect(preview).toHaveTextContent('person-1.jpg');
    expect(preview).toHaveTextContent('Split: train');
  });

  it('explica cómo precalcular la proyección si no existe', async () => {
    routes['/api/pipeline/embedding'] = () =>
      unavailable('data/processed/embedding.json', 'Precalcula con embed.py.');
    render(<ExploreView />);

    expect(await screen.findByTestId('artifact-unavailable')).toHaveTextContent('embed.py');
  });
});
