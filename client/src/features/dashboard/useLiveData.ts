import { useCallback, useEffect, useRef, useState } from 'react';

// T-204: el dashboard se actualiza solo, sin recargar la página. Con este
// stack lo más honesto es un refetch periódico (poll): no hay websockets ni
// stream de eventos del lado del server, y montar uno sería mucha más
// maquinaria de la que el criterio de aceptación pide.

export type LiveState<T> =
  | { status: 'loading' }
  | { status: 'error'; message: string }
  | {
      status: 'ready';
      data: T;
      updatedAt: Date;
      /** Falla de un refetch posterior: se sigue mostrando el último dato bueno. */
      warning: string | null;
    };

export const DEFAULT_REFRESH_MS = 5000;

export function useLiveData<T>(fetcher: () => Promise<T>, intervalMs: number = DEFAULT_REFRESH_MS) {
  const [state, setState] = useState<LiveState<T>>({ status: 'loading' });
  const fetcherRef = useRef(fetcher);
  // Identifica la petición en curso: descarta respuestas que llegan fuera
  // de orden (un poll lento no debe pisar a uno más nuevo).
  const currentRequest = useRef(0);

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  const refresh = useCallback(async () => {
    const requestId = ++currentRequest.current;
    try {
      const data = await fetcherRef.current();
      if (requestId === currentRequest.current) {
        setState({ status: 'ready', data, updatedAt: new Date(), warning: null });
      }
    } catch (error) {
      if (requestId !== currentRequest.current) {
        return;
      }
      const message = (error as Error).message;
      // Si ya había datos en pantalla, un poll fallido no los borra: se
      // avisa del problema y se conserva la última lectura buena.
      setState((previous) =>
        previous.status === 'ready'
          ? { ...previous, warning: message }
          : { status: 'error', message },
      );
    }
  }, []);

  useEffect(() => {
    void refresh();

    const interval = setInterval(() => {
      // Con la pestaña oculta no hay nadie mirando: no tiene sentido seguir
      // pegándole a la API cada N segundos.
      if (!document.hidden) {
        void refresh();
      }
    }, intervalMs);

    const refreshWhenVisible = () => {
      if (!document.hidden) {
        void refresh();
      }
    };
    document.addEventListener('visibilitychange', refreshWhenVisible);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', refreshWhenVisible);
      // Invalida cualquier respuesta en vuelo al desmontar.
      currentRequest.current += 1;
    };
  }, [refresh, intervalMs]);

  return { state, refresh };
}
