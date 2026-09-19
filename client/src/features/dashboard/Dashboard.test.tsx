import { act, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { Dashboard } from './Dashboard';

// SPEC-10 (features/dashboard_metrics.feature): las métricas y gráficas del
// dashboard reflejan datos reales de la API, nunca valores fijos.
//
// T-204: además, el dashboard consume la telemetría real de los analizadores
// (T-202) y se actualiza solo, sin que nadie recargue la página.

const summary = {
  totalImages: 10,
  annotatedImages: 3,
  totalBoundingBoxes: 15,
  totalCategories: 4,
};

const objectsByCategory = [
  { categoryId: 1, categoryName: 'car', color: '#e63946', objectCount: 7 },
  { categoryId: 2, categoryName: 'person', color: '#2a9d8f', objectCount: 5 },
  { categoryId: 3, categoryName: 'dog', color: '#f4a261', objectCount: 2 },
  { categoryId: 4, categoryName: 'bicycle', color: '#264653', objectCount: 1 },
];

// Misma forma que escribe pipeline/scripts/analyze.py en
// data/processed/quality_metrics.json (los 5 reportes Pydantic de T-202).
const qualityMetrics = {
  generatedAt: '2026-09-18T09:30:00.000Z',
  source: 'data/processed/quality_metrics.json',
  metrics: {
    small_objects: {
      threshold_px: 32,
      total_annotations: 120,
      small_count: 18,
      percentage_below_threshold: 15.0,
      most_affected_category: 'person',
      offending_sample_ids: [3, 7, 11],
    },
    class_imbalance: {
      counts: { car: 214, person: 208 },
      majority_minority_ratio: 1.0288461538,
      classes_below_minimum: ['car', 'person'],
    },
    invalid_boxes: {
      total_annotations: 120,
      invalid: [
        { annotation_id: 5, reasons: ['zero_width'] },
        { annotation_id: 9, reasons: ['out_of_image_bounds', 'zero_width'] },
      ],
    },
    spatial_bias: {
      count: 120,
      mean: 4820.5,
      median: 3100.0,
      p10: 900.0,
      p25: 1800.0,
      p75: 6400.0,
      p90: 11000.0,
    },
    duplicates: {
      distance_threshold: 8,
      pairs: [{ image_id_a: 100015, image_id_b: 100016, hash_distance: 4, similarity: 0.9375 }],
    },
  },
};

// Compuerta evaluada por el server: quality.yaml contra la telemetría del
// pipeline. Un fail en rojo bloquea; un warn en rojo solo se reporta.
const gate = {
  passed: false,
  failedChecks: 2,
  warnings: 1,
  checks: [
    {
      name: 'min_images_per_class',
      value: 214,
      threshold: 300,
      direction: 'gte',
      severity: 'fail',
      passed: false,
      evaluated: true,
      offendingSamples: ['car', 'person'],
    },
    {
      name: 'invalid_boxes_count',
      value: 9,
      threshold: 5,
      direction: 'lte',
      severity: 'warn',
      passed: false,
      evaluated: true,
      offendingSamples: ['5', '9'],
    },
  ],
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

// Handlers por URL (no `mockResolvedValueOnce` en cadena): con el poll de
// T-204 el orden y la cantidad de llamadas dejan de ser fijos, y además
// permite cambiar lo que responde la API a mitad de la prueba para verificar
// que la UI se actualiza sola.
let handlers: Record<string, () => Response>;

function defaultHandlers(): Record<string, () => Response> {
  return {
    '/api/dashboard/summary': () => jsonResponse(summary),
    '/api/dashboard/objects-by-category': () => jsonResponse({ objectsByCategory }),
    '/api/dashboard/quality-metrics': () => jsonResponse(qualityMetrics),
    '/api/pipeline/gate': () => jsonResponse(gate),
  };
}

describe('Dashboard', () => {
  beforeEach(() => {
    handlers = defaultHandlers();
    vi.stubGlobal(
      'fetch',
      vi.fn((url: string) => {
        const handler = handlers[url];
        return Promise.resolve(handler ? handler() : jsonResponse({ error: 'no handler' }, 404));
      }),
    );
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.useRealTimers();
  });

  it('muestra las métricas y el progreso reales que devuelve la API', async () => {
    render(<Dashboard />);

    expect(await screen.findByTestId('metric-total-images')).toHaveTextContent('10');
    expect(screen.getByTestId('metric-annotated-images')).toHaveTextContent('3');
    expect(screen.getByTestId('metric-total-boxes')).toHaveTextContent('15');
    expect(screen.getByTestId('metric-total-categories')).toHaveTextContent('4');

    // Progreso: 3 de 10 (30%) — no un porcentaje fijo.
    expect(screen.getByText(/3 de 10/)).toBeInTheDocument();
    expect(screen.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '30');
  });

  it('grafica objetos por categoría con los datos reales de la API', async () => {
    render(<Dashboard />);

    await screen.findByTestId('metric-total-images');
    // Acotado al panel del chart: los nombres de clase también aparecen en
    // la telemetría del pipeline, y sin acotar la búsqueda sería ambigua.
    const chartPanel = screen.getByText('Objetos por clase').closest('.dashboard__panel');
    expect(chartPanel).not.toBeNull();
    for (const category of objectsByCategory) {
      expect(
        within(chartPanel as HTMLElement).getByText(category.categoryName),
      ).toBeInTheDocument();
    }
  });

  it('muestra un mensaje de error si la API falla', async () => {
    handlers['/api/dashboard/summary'] = () => jsonResponse({ error: 'boom' }, 500);
    handlers['/api/dashboard/objects-by-category'] = () => jsonResponse({ error: 'boom' }, 500);

    render(<Dashboard />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('muestra la telemetría real de los 5 analizadores del pipeline', async () => {
    render(<Dashboard />);

    expect(await screen.findByTestId('telemetry-small-percentage')).toHaveTextContent('15.0%');
    expect(screen.getByTestId('telemetry-small-count')).toHaveTextContent('18 / 120');
    expect(screen.getByTestId('telemetry-small-most-affected')).toHaveTextContent('person');
    expect(screen.getByTestId('telemetry-imbalance-ratio')).toHaveTextContent('1.03x');
    expect(screen.getByTestId('telemetry-below-minimum-count')).toHaveTextContent('2');
    expect(screen.getByTestId('telemetry-class-car')).toHaveTextContent('214');
    expect(screen.getByTestId('telemetry-invalid-count')).toHaveTextContent('2 / 120');
    // Dos cajas distintas comparten la razón zero_width: se agrupa, no se repite.
    expect(screen.getByTestId('telemetry-reason-zero_width')).toHaveTextContent('2');
    expect(screen.getByTestId('telemetry-spatial-mean')).toHaveTextContent('4820.50');
    expect(screen.getByTestId('telemetry-spatial-median')).toHaveTextContent('3100');
    expect(screen.getByText(/p10 900 · p25 1800/)).toBeInTheDocument();
    expect(screen.getByTestId('telemetry-duplicates-count')).toHaveTextContent('1');
    // La pantalla dice de qué artefacto salieron los números y cuándo se generó.
    expect(screen.getByTestId('telemetry-source')).toHaveTextContent(
      'data/processed/quality_metrics.json',
    );
  });

  it('explica qué falta cuando el pipeline todavía no dejó su artefacto en disco', async () => {
    handlers['/api/dashboard/quality-metrics'] = () =>
      jsonResponse(
        {
          error: 'La telemetría del pipeline todavía no está materializada en disco.',
          expectedPath: 'data/processed/quality_metrics.json',
          hint: 'Corre `dvc pull` (o `dvc repro`) para materializar los artefactos del pipeline.',
        },
        503,
      );

    render(<Dashboard />);

    const message = await screen.findByTestId('telemetry-unavailable');
    expect(message).toHaveTextContent('dvc pull');
    // Las métricas de la BD se siguen viendo: una fuente caída no tumba la otra.
    expect(screen.getByTestId('metric-total-images')).toHaveTextContent('10');
  });

  it('refleja datos nuevos sin que nadie recargue la página', async () => {
    // shouldAdvanceTime: sin esto, los `waitFor` de Testing Library se
    // quedan colgados porque su propio timeout también estaría congelado.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<Dashboard />);

    await waitFor(() => expect(screen.getByTestId('metric-total-images')).toHaveTextContent('10'));

    // Cambia el dato en la fuente (como si alguien anotara una imagen más):
    // la UI debe reflejarlo sola, sin volver a montar nada.
    handlers['/api/dashboard/summary'] = () =>
      jsonResponse({ ...summary, totalImages: 11, annotatedImages: 4 });
    handlers['/api/dashboard/quality-metrics'] = () =>
      jsonResponse({
        ...qualityMetrics,
        metrics: {
          ...qualityMetrics.metrics,
          small_objects: { ...qualityMetrics.metrics.small_objects, small_count: 21 },
        },
      });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(screen.getByTestId('metric-total-images')).toHaveTextContent('11');
    expect(screen.getByTestId('metric-annotated-images')).toHaveTextContent('4');
    expect(screen.getByTestId('telemetry-small-count')).toHaveTextContent('21 / 120');
  });

  it('conserva la última lectura buena si un refresco posterior falla', async () => {
    // shouldAdvanceTime: sin esto, los `waitFor` de Testing Library se
    // quedan colgados porque su propio timeout también estaría congelado.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<Dashboard />);

    await waitFor(() => expect(screen.getByTestId('metric-total-images')).toHaveTextContent('10'));

    handlers['/api/dashboard/summary'] = () => jsonResponse({ error: 'caída' }, 500);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(5000);
    });

    expect(await screen.findByRole('status')).toHaveTextContent('El último refresco falló');
    // El dato viejo sigue en pantalla en vez de desaparecer.
    expect(screen.getByTestId('metric-total-images')).toHaveTextContent('10');
  });

  it('no consulta la API mientras la pestaña está oculta', async () => {
    // shouldAdvanceTime: sin esto, los `waitFor` de Testing Library se
    // quedan colgados porque su propio timeout también estaría congelado.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    render(<Dashboard />);

    await waitFor(() => expect(screen.getByTestId('metric-total-images')).toHaveTextContent('10'));
    const callsAfterFirstLoad = (fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.length;

    const hidden = vi.spyOn(document, 'hidden', 'get').mockReturnValue(true);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(15000);
    });
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBe(
      callsAfterFirstLoad,
    );

    // Al volver a la pestaña se refresca de inmediato, sin esperar al intervalo.
    hidden.mockReturnValue(false);
    await act(async () => {
      document.dispatchEvent(new Event('visibilitychange'));
      await vi.advanceTimersByTimeAsync(0);
    });
    expect((fetch as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBeGreaterThan(
      callsAfterFirstLoad,
    );

    hidden.mockRestore();
  });

  it('muestra el estado de la compuerta y cuántos checks fallan, calculados por el server', async () => {
    render(<Dashboard />);

    expect(await screen.findByTestId('gate-state')).toHaveTextContent('COMPUERTA: BLOQUEA');
    expect(screen.getByTestId('metric-failed-checks')).toHaveTextContent('2');
    expect(screen.getByTestId('gate-summary')).toHaveTextContent('1 warn, no bloquean');
    expect(screen.getByTestId('gate-failing-min_images_per_class')).toHaveTextContent(
      '214 (debe ser ≥ 300)',
    );
    expect(screen.getByTestId('gate-failing-min_images_per_class')).toHaveTextContent(
      'car, person',
    );
  });

  it('con la compuerta en verde muestra PASA y cero checks fallidos', async () => {
    handlers['/api/pipeline/gate'] = () =>
      jsonResponse({ passed: true, failedChecks: 0, warnings: 0, checks: [] });

    render(<Dashboard />);

    expect(await screen.findByTestId('gate-state')).toHaveTextContent('COMPUERTA: PASA');
    expect(screen.getByTestId('metric-failed-checks')).toHaveTextContent('0');
  });

  it('si la compuerta no se puede evaluar, lo dice y el resto del Overview sigue', async () => {
    handlers['/api/pipeline/gate'] = () =>
      jsonResponse(
        {
          error: 'El artefacto todavía no está materializado.',
          expectedPath: 'data/processed/quality_metrics.json',
          hint: 'Corre `dvc pull`.',
        },
        503,
      );

    render(<Dashboard />);

    expect(await screen.findByTestId('gate-unavailable')).toHaveTextContent('dvc pull');
    expect(screen.getByTestId('metric-total-images')).toHaveTextContent('10');
    expect(screen.queryByTestId('metric-failed-checks')).not.toBeInTheDocument();
  });
});
