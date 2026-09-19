import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ContractsView } from './ContractsView';

// T-104: la sexta pantalla muestra los tres contratos congelados de T-101
// completos (quality.json, splits.json, versions.json), sin inventar datos
// ni esconder campos del contrato.

const quality = {
  passed: false,
  checks: [
    {
      name: 'min_images_per_class',
      value: 214.0,
      threshold: 300.0,
      direction: 'gte',
      severity: 'fail',
      passed: false,
      offending_samples: ['car', 'person'],
    },
    {
      name: 'invalid_boxes_count',
      value: 0.0,
      threshold: 5.0,
      direction: 'lte',
      severity: 'warn',
      passed: true,
      offending_samples: [],
    },
  ],
};

const splits = {
  seed: 42,
  ratios: { train: 0.7, val: 0.15, test: 0.15 },
  assignments: { '1': 'train', '2': 'train', '3': 'train', '4': 'train', '5': 'val', '6': 'test' },
  counts: { train: 4, val: 1, test: 1 },
};

const versions = {
  current: 'v0.2.0',
  releases: [
    {
      version: 'v0.1.0',
      message: 'Dataset inicial de muestra (30 imagenes, 2 clases)',
      created_at: '2026-09-10T12:00:00Z',
      dvc_rev: '6f96b83',
      diff_vs_previous: null,
    },
    {
      version: 'v0.2.0',
      message: 'Primer lote real anotado por el equipo',
      created_at: '2026-09-18T08:00:00Z',
      dvc_rev: 'b3ea54a',
      diff_vs_previous: {
        from: 'v0.1.0',
        to: 'v0.2.0',
        images_added: [100015, 100016, 200015],
        images_removed: [],
        boxes_added: [32, 33, 34],
        boxes_removed: [],
        images_per_class: { car: 214, person: 208 },
        classes_below_minimum: ['car', 'person'],
      },
    },
  ],
};

const CONTRACT_BODIES: Record<string, unknown> = {
  '/api/contracts/quality': quality,
  '/api/contracts/splits': splits,
  '/api/contracts/versions': versions,
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

function stubContractsApi() {
  const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
  fetchMock.mockImplementation((url: string) =>
    Promise.resolve(jsonResponse(CONTRACT_BODIES[url] ?? {})),
  );
  return fetchMock;
}

describe('ContractsView', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('muestra cada check de quality.json con valor, umbral, severidad y muestras ofensoras', async () => {
    stubContractsApi();

    render(<ContractsView />);

    expect(await screen.findByTestId('quality-passed')).toHaveTextContent('Compuerta bloqueada');

    const failingCheck = screen.getByTestId('quality-check-min_images_per_class');
    expect(within(failingCheck).getByText('214')).toBeInTheDocument();
    expect(within(failingCheck).getByText('>= 300')).toBeInTheDocument();
    expect(within(failingCheck).getByText('fail (bloquea)')).toBeInTheDocument();
    expect(within(failingCheck).getByText('no cumple')).toBeInTheDocument();
    expect(within(failingCheck).getByText('car')).toBeInTheDocument();
    expect(within(failingCheck).getByText('person')).toBeInTheDocument();

    // El warn no bloquea, pero igual aparece con su valor y su umbral.
    const warnCheck = screen.getByTestId('quality-check-invalid_boxes_count');
    expect(within(warnCheck).getByText('<= 5')).toBeInTheDocument();
    expect(within(warnCheck).getByText('warn (no bloquea)')).toBeInTheDocument();
    expect(within(warnCheck).getByText('cumple')).toBeInTheDocument();
  });

  it('muestra seed, counts y la asignación imagen → split de splits.json', async () => {
    stubContractsApi();

    render(<ContractsView />);

    expect(await screen.findByTestId('splits-seed')).toHaveTextContent('seed 42');
    expect(screen.getByTestId('splits-count-train')).toHaveTextContent('4');
    expect(screen.getByTestId('splits-count-val')).toHaveTextContent('1');
    expect(screen.getByTestId('splits-count-test')).toHaveTextContent('1');

    // Las 6 imágenes del contrato aparecen, no solo un resumen.
    expect(screen.getAllByTestId(/^splits-assignment-/)).toHaveLength(6);
    expect(screen.getByTestId('splits-assignment-5')).toHaveTextContent('val');
    expect(screen.getByTestId('splits-assignment-6')).toHaveTextContent('test');
  });

  it('muestra el historial de versions.json con el diff completo del release actual', async () => {
    stubContractsApi();

    render(<ContractsView />);

    expect(await screen.findByTestId('versions-current')).toHaveTextContent('v0.2.0');

    const currentRelease = screen.getByTestId('release-v0.2.0');
    expect(within(currentRelease).getByText('b3ea54a', { exact: false })).toBeInTheDocument();
    expect(within(currentRelease).getByText(/Diff v0\.1\.0 → v0\.2\.0/)).toBeInTheDocument();
    expect(within(currentRelease).getByText('Imágenes agregadas (3)')).toBeInTheDocument();
    expect(within(currentRelease).getByText('100015')).toBeInTheDocument();
    expect(within(currentRelease).getByText('Cajas agregadas (3)')).toBeInTheDocument();
    expect(within(currentRelease).getByText('32')).toBeInTheDocument();
    expect(within(currentRelease).getByTestId('release-class-car')).toHaveTextContent('car: 214');
    expect(within(currentRelease).getByText('Clases bajo el mínimo (2)')).toBeInTheDocument();

    // El primer release no tiene diff: se dice explícitamente, no se omite.
    const firstRelease = screen.getByTestId('release-v0.1.0');
    expect(within(firstRelease).getByText(/primer release/)).toBeInTheDocument();
  });

  it('avisa en pantalla si un contrato no se puede cargar, en vez de quedarse en blanco', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockImplementation((url: string) =>
      Promise.resolve(
        url === '/api/contracts/splits'
          ? jsonResponse({ error: 'no existe' }, 404)
          : jsonResponse(CONTRACT_BODIES[url] ?? {}),
      ),
    );

    render(<ContractsView />);

    expect(await screen.findByRole('alert')).toHaveTextContent('/api/contracts/splits');
  });

  it('vuelve a pedir los contratos al presionar "Actualizar"', async () => {
    const fetchMock = stubContractsApi();

    render(<ContractsView />);
    await screen.findByTestId('quality-passed');
    expect(fetchMock).toHaveBeenCalledTimes(3);

    fireEvent.click(screen.getByRole('button', { name: 'Actualizar' }));

    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(6));
  });
});
