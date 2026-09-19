import type { CSSProperties } from 'react';
import { Bar, BarChart, Cell, Tooltip, XAxis, YAxis } from 'recharts';
import {
  type DashboardSummary,
  type ObjectsByCategory,
  fetchDashboardSummary,
  fetchObjectsByCategory,
} from '../../api/dashboard';
import { fetchGate } from '../../api/pipeline';
import { fetchQualityMetrics } from '../../api/telemetry';
import { GateStatus } from '../pipeline/GateStatus';
import { PipelineTelemetry } from './PipelineTelemetry';
import './dashboard.css';
import { DEFAULT_REFRESH_MS, useLiveData } from './useLiveData';

type DatabaseMetrics = {
  summary: DashboardSummary;
  objectsByCategory: ObjectsByCategory;
};

// Definido fuera del componente a propósito: `useLiveData` lo usa como
// fuente estable del poll, y una función nueva en cada render reiniciaría
// el intervalo sin parar.
async function fetchDatabaseMetrics(): Promise<DatabaseMetrics> {
  const [summary, objectsByCategory] = await Promise.all([
    fetchDashboardSummary(),
    fetchObjectsByCategory(),
  ]);
  return { summary, objectsByCategory };
}

export function Dashboard() {
  // Dos fuentes independientes: las métricas de la BD (portal) y la
  // telemetría real del pipeline (T-202). Si una falla o todavía no está
  // materializada, la otra se sigue mostrando.
  const database = useLiveData(fetchDatabaseMetrics);
  const telemetry = useLiveData(fetchQualityMetrics);
  // Tercera fuente: la compuerta de calidad (quality.yaml evaluado contra la
  // telemetría). Si no se puede evaluar, el resto del Overview sigue igual.
  const gate = useLiveData(fetchGate);

  function refreshAll() {
    void database.refresh();
    void telemetry.refresh();
    void gate.refresh();
  }

  if (database.state.status === 'loading') {
    return (
      <section aria-label="Dashboard" className="dashboard">
        <output className="dashboard__hint">Cargando métricas...</output>
      </section>
    );
  }

  if (database.state.status === 'error') {
    return (
      <section aria-label="Dashboard" className="dashboard">
        <p role="alert" className="dashboard__error">
          No se pudieron cargar las métricas del dashboard: {database.state.message}
        </p>
      </section>
    );
  }

  const { summary, objectsByCategory } = database.state.data;
  const progressPercent =
    summary.totalImages === 0
      ? 0
      : Math.round((summary.annotatedImages / summary.totalImages) * 100);

  return (
    <section aria-label="Dashboard" className="dashboard">
      <div className="dashboard__panel-header">
        <h2 className="dashboard__title">Dashboard</h2>
        <div className="dashboard__live">
          <span className="dashboard__source" data-testid="dashboard-updated-at">
            Actualizado {database.state.updatedAt.toLocaleTimeString()} · se refresca solo cada{' '}
            {DEFAULT_REFRESH_MS / 1000} s
          </span>
          <button type="button" className="dashboard__refresh" onClick={refreshAll}>
            Actualizar ahora
          </button>
        </div>
      </div>

      {/* Un refetch fallido no borra lo que ya estaba en pantalla: se avisa
          y se sigue mostrando la última lectura buena. */}
      {database.state.warning !== null && (
        <output className="dashboard__warning">
          El último refresco falló ({database.state.warning}); se muestra la lectura anterior.
        </output>
      )}

      <GateStatus state={gate.state} />

      <div className="dashboard__metrics">
        <div className="dashboard__metric" style={{ '--metric-color': '#3fa9f5' } as CSSProperties}>
          <span className="dashboard__metric-label">Total de imágenes</span>
          <span className="dashboard__metric-value" data-testid="metric-total-images">
            {summary.totalImages}
          </span>
        </div>
        <div className="dashboard__metric" style={{ '--metric-color': '#2dd4a7' } as CSSProperties}>
          <span className="dashboard__metric-label">Imágenes anotadas</span>
          <span className="dashboard__metric-value" data-testid="metric-annotated-images">
            {summary.annotatedImages}
          </span>
        </div>
        <div className="dashboard__metric" style={{ '--metric-color': '#f4a261' } as CSSProperties}>
          <span className="dashboard__metric-label">Total de bounding boxes</span>
          <span className="dashboard__metric-value" data-testid="metric-total-boxes">
            {summary.totalBoundingBoxes}
          </span>
        </div>
        <div className="dashboard__metric" style={{ '--metric-color': '#a78bfa' } as CSSProperties}>
          <span className="dashboard__metric-label">Categorías</span>
          <span className="dashboard__metric-value" data-testid="metric-total-categories">
            {summary.totalCategories}
          </span>
        </div>
        {gate.state.status === 'ready' && gate.state.data.available && (
          <div
            className="dashboard__metric"
            style={
              {
                '--metric-color': gate.state.data.data.failedChecks > 0 ? '#e5484d' : '#2dd4a7',
              } as CSSProperties
            }
          >
            <span className="dashboard__metric-label">Checks fallidos</span>
            <span className="dashboard__metric-value" data-testid="metric-failed-checks">
              {gate.state.data.data.failedChecks}
            </span>
          </div>
        )}
      </div>

      <div className="dashboard__panel">
        <h3 className="dashboard__section-title">Progreso de anotación</h3>
        <p className="dashboard__progress-text">
          {summary.annotatedImages} de {summary.totalImages} imágenes anotadas ({progressPercent}%)
        </p>
        <div
          role="progressbar"
          tabIndex={0}
          aria-valuenow={progressPercent}
          aria-valuemin={0}
          aria-valuemax={100}
          className="dashboard__progress-track"
        >
          <div className="dashboard__progress-fill" style={{ width: `${progressPercent}%` }} />
        </div>
      </div>

      <div className="dashboard__panel">
        <h3 className="dashboard__section-title">Objetos por clase</h3>
        {/* Ancho fijo (no ResponsiveContainer): en jsdom, ResponsiveContainer
            nunca mide un tamaño real (no hay ResizeObserver que dispare), así
            que no renderiza nada y el chart queda imposible de testear. Con
            ancho fijo se sacrifica el resize automático a cambio de un chart
            que sí se puede probar de verdad; el overflow-x cubre pantallas
            angostas. (Comentario y decisión originales de JuanPa, preservados
            — sigue aplicando igual con el rediseño.) */}
        <div className="dashboard__chart-scroll">
          <BarChart
            width={600}
            height={280}
            data={objectsByCategory}
            margin={{ top: 8, right: 16, left: 0, bottom: 8 }}
          >
            <XAxis
              dataKey="categoryName"
              tickLine={false}
              axisLine={{ stroke: '#3d434c' }}
              tick={{ fill: '#8b8f98', fontSize: 12, fontFamily: 'IBM Plex Sans, sans-serif' }}
            />
            <YAxis
              allowDecimals={false}
              tickLine={false}
              axisLine={{ stroke: '#3d434c' }}
              tick={{ fill: '#8b8f98', fontSize: 12, fontFamily: 'IBM Plex Mono, monospace' }}
            />
            <Tooltip
              contentStyle={{
                background: '#1c1f24',
                border: '1px solid #3d434c',
                color: '#e7e5e0',
              }}
              cursor={{ fill: 'rgba(63, 169, 245, 0.08)' }}
            />
            <Bar dataKey="objectCount" radius={[2, 2, 0, 0]}>
              {objectsByCategory.map((category) => (
                <Cell key={category.categoryId} fill={category.color} />
              ))}
            </Bar>
          </BarChart>
        </div>
      </div>

      {telemetry.state.status === 'loading' && (
        <output className="dashboard__hint">Cargando telemetría del pipeline...</output>
      )}
      {telemetry.state.status === 'error' && (
        <p role="alert" className="dashboard__error">
          No se pudo cargar la telemetría del pipeline: {telemetry.state.message}
        </p>
      )}
      {telemetry.state.status === 'ready' && <PipelineTelemetry result={telemetry.state.data} />}
    </section>
  );
}
