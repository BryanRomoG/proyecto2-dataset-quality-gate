import { render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { FrozenContracts } from './FrozenContracts';

// T-104: las 6ta pantalla renderiza los 3 contratos congelados por Bryan en
// T-101 (quality.json, splits.json, versions.json) tal cual los sirve la API.

const quality = {
  passed: false,
  checks: [
    {
      name: 'min_images_per_class',
      value: 214,
      threshold: 300,
      direction: 'gte',
      severity: 'fail',
      passed: false,
      offending_samples: ['car', 'person'],
    },
  ],
};

const splits = {
  seed: 42,
  ratios: { train: 0.7, val: 0.15, test: 0.15 },
  assignments: { '1': 'train', '2': 'val' },
  counts: { train: 1, val: 1, test: 0 },
};

const versions = {
  current: 'v0.2.0',
  releases: [
    {
      version: 'v0.1.0',
      message: 'Dataset inicial de muestra',
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
        images_added: [1, 2, 3],
        images_removed: [],
        boxes_added: [1, 2],
        boxes_removed: [],
        images_per_class: { car: 214, person: 208 },
        classes_below_minimum: ['car', 'person'],
      },
    },
  ],
};

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('FrozenContracts', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('muestra la versión actual y el historial de versiones', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse(quality))
      .mockResolvedValueOnce(jsonResponse(splits))
      .mockResolvedValueOnce(jsonResponse(versions));

    render(<FrozenContracts />);

    expect(await screen.findByTestId('versions-current')).toHaveTextContent('v0.2.0');
    expect(screen.getByText('v0.1.0')).toBeInTheDocument();
    expect(screen.getByText(/Clases bajo el mínimo/)).toBeInTheDocument();
  });

  it('muestra el estado del quality gate y sus chequeos', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse(quality))
      .mockResolvedValueOnce(jsonResponse(splits))
      .mockResolvedValueOnce(jsonResponse(versions));

    render(<FrozenContracts />);

    expect(await screen.findByTestId('quality-gate-status')).toHaveTextContent('NO PASA');
    expect(screen.getByText('min_images_per_class')).toBeInTheDocument();
  });

  it('muestra el resumen y las asignaciones de splits', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse(quality))
      .mockResolvedValueOnce(jsonResponse(splits))
      .mockResolvedValueOnce(jsonResponse(versions));

    render(<FrozenContracts />);

    await screen.findByTestId('versions-current');
    expect(screen.getByText(/Seed: 42/)).toBeInTheDocument();
    expect(screen.getByText('train')).toBeInTheDocument();
  });

  it('muestra un mensaje de error si algún contrato falla al cargar', async () => {
    const fetchMock = fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock
      .mockResolvedValueOnce(jsonResponse({ error: 'boom' }, 500))
      .mockResolvedValueOnce(jsonResponse(splits))
      .mockResolvedValueOnce(jsonResponse(versions));

    render(<FrozenContracts />);

    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
