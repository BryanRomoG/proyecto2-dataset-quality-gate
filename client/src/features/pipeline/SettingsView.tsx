import { type FormEvent, useState } from 'react';
import {
  type Gate,
  type Policy,
  SettingsValidationError,
  fetchSettings,
  saveSettings,
} from '../../api/pipeline';
import { ArtifactView } from './ArtifactView';

// Sección 7.5: editar los umbrales de quality.yaml desde la UI. El guardado
// escribe el archivo de verdad (PUT /api/pipeline/settings) y la respuesta
// trae la compuerta re-evaluada con la política nueva, para ver el efecto
// del cambio sin esperar a la siguiente corrida del pipeline.

// El curso exige >= 300 imágenes por clase con severidad `fail`. Se avisa,
// pero no se bloquea: subir el umbral para probar la compuerta es legítimo.
const COURSE_MINIMUM = 300;

type Draft = Record<string, { threshold: string; severity: 'warn' | 'fail' }>;

function toDraft(policy: Policy): Draft {
  return Object.fromEntries(
    Object.entries(policy.checks).map(([name, check]) => [
      name,
      { threshold: String(check.threshold), severity: check.severity },
    ]),
  );
}

function courseWarning(draft: Draft): string | null {
  const check = draft.min_images_per_class;
  if (!check) return null;
  const threshold = Number(check.threshold);
  if (threshold < COURSE_MINIMUM || check.severity !== 'fail') {
    return `El curso exige min_images_per_class ≥ ${COURSE_MINIMUM} con severidad fail; con este valor el release entregado podría no cumplir el mínimo.`;
  }
  return null;
}

function SettingsForm({ initial }: { initial: Policy }) {
  const [saved, setSaved] = useState(initial);
  const [draft, setDraft] = useState<Draft>(() => toDraft(initial));
  const [status, setStatus] = useState<
    | { kind: 'idle' }
    | { kind: 'saving' }
    | { kind: 'saved'; gate: Gate | null }
    | { kind: 'error'; messages: string[] }
  >({ kind: 'idle' });

  const dirty = JSON.stringify(draft) !== JSON.stringify(toDraft(saved));
  const warning = courseWarning(draft);

  function update(name: string, patch: Partial<Draft[string]>) {
    setDraft((current) => ({
      ...current,
      [name]: { ...(current[name] as Draft[string]), ...patch },
    }));
    setStatus({ kind: 'idle' });
  }

  async function submit(event: FormEvent) {
    event.preventDefault();

    // Un campo vacío o no numérico no se manda: Number('') sería 0 y
    // guardaría un umbral que nadie escribió.
    const invalid = Object.entries(draft).filter(
      ([, check]) => check.threshold.trim() === '' || Number.isNaN(Number(check.threshold)),
    );
    if (invalid.length > 0) {
      setStatus({
        kind: 'error',
        messages: invalid.map(([name]) => `${name}: el umbral debe ser un número`),
      });
      return;
    }

    setStatus({ kind: 'saving' });
    try {
      const result = await saveSettings({
        checks: Object.fromEntries(
          Object.entries(draft).map(([name, check]) => [
            name,
            { threshold: Number(check.threshold), severity: check.severity },
          ]),
        ),
      });
      setSaved(result.policy);
      setDraft(toDraft(result.policy));
      setStatus({ kind: 'saved', gate: result.gate });
    } catch (error) {
      setStatus({
        kind: 'error',
        messages:
          error instanceof SettingsValidationError ? error.issues : [(error as Error).message],
      });
    }
  }

  return (
    <form className="pipeline__form" onSubmit={submit} aria-label="Política de la compuerta">
      <p className="dashboard__muted">
        Umbrales de <code>quality.yaml</code>. Al guardar se escribe el archivo y la compuerta se
        vuelve a evaluar con los valores nuevos.
      </p>

      {Object.keys(draft).map((name) => {
        const check = draft[name] as Draft[string];
        return (
          <div className="pipeline__field" key={name}>
            <label htmlFor={`threshold-${name}`}>
              <code>{name}</code>
            </label>
            <input
              id={`threshold-${name}`}
              aria-label={`Umbral de ${name}`}
              type="number"
              min={0}
              step="any"
              value={check.threshold}
              onChange={(event) => update(name, { threshold: event.target.value })}
            />
            <select
              aria-label={`Severidad de ${name}`}
              value={check.severity}
              onChange={(event) =>
                update(name, { severity: event.target.value as 'warn' | 'fail' })
              }
            >
              <option value="fail">fail (bloquea)</option>
              <option value="warn">warn (no bloquea)</option>
            </select>
          </div>
        );
      })}

      {warning && (
        <p className="pipeline__notice" data-testid="course-warning">
          {warning}
        </p>
      )}

      <button
        type="submit"
        className="pipeline__button"
        disabled={!dirty || status.kind === 'saving'}
      >
        {status.kind === 'saving' ? 'Guardando…' : 'Guardar en quality.yaml'}
      </button>

      {status.kind === 'error' && (
        <div role="alert" className="pipeline__error">
          {status.messages.map((message) => (
            <div key={message}>{message}</div>
          ))}
        </div>
      )}

      {status.kind === 'saved' && (
        <output className="dashboard__hint" data-testid="save-result">
          Guardado en quality.yaml.{' '}
          {status.gate
            ? status.gate.passed
              ? 'Con la política nueva la compuerta PASA.'
              : `Con la política nueva la compuerta BLOQUEA (${status.gate.failedChecks} check(s) en rojo).`
            : 'No hay telemetría del pipeline para re-evaluar la compuerta todavía.'}
        </output>
      )}
    </form>
  );
}

export function SettingsView() {
  return (
    // Sin poll: releer cada N segundos no debe pisar lo que se está editando.
    <ArtifactView label="Settings" title="Settings" fetcher={fetchSettings} pollMs={3_600_000}>
      {(data) => <SettingsForm initial={data.policy} />}
    </ArtifactView>
  );
}
