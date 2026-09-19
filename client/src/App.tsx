import { useState } from 'react';
import './App.css';
import { AnnotationWorkspace } from './features/annotations/AnnotationWorkspace';
import { ContractsView } from './features/contracts/ContractsView';
import { Dashboard } from './features/dashboard/Dashboard';
import { ExportCocoButton } from './features/export/ExportCocoButton';
import { ImageUploadPanel } from './features/images/ImageUploadPanel';
import { AnalyzersView } from './features/pipeline/AnalyzersView';
import { ExploreView } from './features/pipeline/ExploreView';
import { SettingsView } from './features/pipeline/SettingsView';
import { SplitsView } from './features/pipeline/SplitsView';
import { VersionsView } from './features/pipeline/VersionsView';
import { ImageSearch } from './features/search/ImageSearch';
type View =
  | 'images'
  | 'annotate'
  | 'dashboard'
  | 'analyzers'
  | 'splits'
  | 'versions'
  | 'settings'
  | 'explore'
  | 'search'
  | 'coco'
  | 'contracts';

// Pantallas de la app de calidad de datasets (sección 7): el Overview es el
// Dashboard de siempre; las demás leen los artefactos del pipeline.
const PIPELINE_VIEWS: { id: View; label: string }[] = [
  { id: 'dashboard', label: 'Overview' },
  { id: 'analyzers', label: 'Analyzers' },
  { id: 'splits', label: 'Splits' },
  { id: 'versions', label: 'Versions' },
  { id: 'settings', label: 'Settings' },
  { id: 'explore', label: 'Explorar' },
];

export function App() {
  const [view, setView] = useState<View>('images');

  return (
    <main>
      <h1 className="app-header">Portal de Anotación de Imágenes</h1>
      <nav className="app-nav">
        <button type="button" onClick={() => setView('images')} disabled={view === 'images'}>
          Imágenes
        </button>
        <button type="button" onClick={() => setView('annotate')} disabled={view === 'annotate'}>
          Anotar
        </button>
        {PIPELINE_VIEWS.map((item) => (
          <button
            type="button"
            key={item.id}
            onClick={() => setView(item.id)}
            disabled={view === item.id}
          >
            {item.label}
          </button>
        ))}
        <button type="button" onClick={() => setView('search')} disabled={view === 'search'}>
          Buscar
        </button>
        <button type="button" onClick={() => setView('coco')} disabled={view === 'coco'}>
          COCO
        </button>
        <button type="button" onClick={() => setView('contracts')} disabled={view === 'contracts'}>
          Contratos
        </button>
      </nav>
      {view === 'images' && (
        <div className="app-light-island">
          <ImageUploadPanel />
        </div>
      )}
      {view === 'annotate' && <AnnotationWorkspace />}
      {view === 'dashboard' && <Dashboard />}
      {view === 'analyzers' && <AnalyzersView />}
      {view === 'splits' && <SplitsView />}
      {view === 'versions' && <VersionsView />}
      {view === 'settings' && <SettingsView />}
      {view === 'explore' && <ExploreView />}
      {view === 'search' && <ImageSearch />}
      {view === 'coco' && (
        <div className="app-light-island">
          <ExportCocoButton />
        </div>
      )}
      {view === 'contracts' && <ContractsView />}
    </main>
  );
}
