import { useCallback, useEffect, useRef, useState } from 'react';
import {
  fetchQualityContract,
  fetchSplitsContract,
  fetchVersionsContract,
} from '../../api/contracts';
import { QualityPanel } from './QualityPanel';
import { SplitsPanel } from './SplitsPanel';
import { VersionsPanel } from './VersionsPanel';
import './contracts.css';
import type { QualityReport, SplitsReport, VersionsReport } from './schemas';

type State =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready';
      quality: QualityReport;
      splits: SplitsReport;
      versions: VersionsReport;
    };

export function ContractsView() {
  const [state, setState] = useState<State>({ status: 'loading' });
  // Identifica la carga en curso: si el usuario presiona "Actualizar" dos
  // veces (o desmonta la pantalla) antes de que vuelva la primera, la
  // respuesta vieja se descarta en vez de pisar a la nueva.
  const currentRequest = useRef(0);

  const load = useCallback(async () => {
    const requestId = ++currentRequest.current;
    setState({ status: 'loading' });
    try {
      // Los tres contratos se piden en paralelo: son archivos
      // independientes y ninguno depende de la respuesta del otro.
      const [quality, splits, versions] = await Promise.all([
        fetchQualityContract(),
        fetchSplitsContract(),
        fetchVersionsContract(),
      ]);
      if (requestId === currentRequest.current) {
        setState({ status: 'ready', quality, splits, versions });
      }
    } catch (error) {
      if (requestId === currentRequest.current) {
        setState({ status: 'error', message: (error as Error).message });
      }
    }
  }, []);

  useEffect(() => {
    void load();
    return () => {
      // Al desmontar, cualquier carga en vuelo queda invalidada.
      currentRequest.current += 1;
    };
  }, [load]);

  return (
    <section aria-label="Contratos del dataset" className="contracts">
      <header className="contracts__header">
        <div>
          <h2 className="contracts__title">Contratos del dataset</h2>
          <p className="contracts__subtitle">
            Compuerta de calidad, splits y versiones, leídos de los contratos congelados en T-101 (
            <code>contracts/examples/</code>) vía <code>/api/contracts/*</code>. Todavía no son
            datos reales del pipeline: eso entra en T-204.
          </p>
        </div>
        <button type="button" className="contracts__reload" onClick={() => void load()}>
          Actualizar
        </button>
      </header>

      {state.status === 'loading' && (
        <output className="contracts__hint">Cargando contratos...</output>
      )}

      {state.status === 'error' && (
        <p role="alert" className="contracts__error">
          No se pudieron cargar los contratos: {state.message}
        </p>
      )}

      {state.status === 'ready' && (
        <>
          <QualityPanel report={state.quality} />
          <SplitsPanel report={state.splits} />
          <VersionsPanel report={state.versions} />
        </>
      )}
    </section>
  );
}
