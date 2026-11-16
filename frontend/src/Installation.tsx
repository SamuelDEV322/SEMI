import { useState, useEffect, useCallback } from "react";
import { Bot, Leaf } from "lucide-react";
import { request, setupAction, api } from "./services/api";
import { ThemeSelector } from "./components/ThemeSelector";
import { SectorManager } from "./components/SectorManager";
import { PointEditor } from "./components/PointEditor";
import { TrialTools } from "./components/TrialTools";
import { Connection, ErrorNotice, dateTime } from "./components/ui";
import { usePolling } from "./hooks/usePolling";
import { Dashboard } from "./App";
import type { SetupPlot, SetupAction } from "./types/setup";
export default function Installation() {
  const [plot, setPlot] = useState<SetupPlot | null>(null),
    [loaded, setLoaded] = useState(false),
    [initialError, setInitialError] = useState(false),
    [error, setError] = useState(""),
    [technical, setTechnical] = useState(""),
    [busy, setBusy] = useState(false),
    [force, setForce] = useState(false),
    [paused, setPaused] = useState(false),
    [name, setName] = useState("Mi cafetal"),
    [selected, setSelected] = useState<number>();
  const apply = (p: SetupPlot) => {
    localStorage.setItem("semi-plot", String(p.id));
    setPlot(p);
    setName(p.name);
  };
  const load = useCallback(async () => {
    setLoaded(false);
    setInitialError(false);
    setError("");
    try {
      const p = await request<SetupPlot | null>("setup/");
      if (p) apply(p);
      else setPlot(null);
    } catch (e) {
      setInitialError(true);
      setTechnical(String(e));
      setError(
        "No pudimos cargar tus datos. Comprueba la conexión e inténtalo de nuevo",
      );
    } finally {
      setLoaded(true);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  const act: SetupAction = async (action, extra = {}) => {
    setBusy(true);
    setError("");
    try {
      const p = await setupAction({ action, ...extra });
      apply(p);
      return p;
    } catch (e) {
      setTechnical(String(e));
      setError(
        "No pudimos guardar el cambio. Comprueba la conexión e inténtalo de nuevo.",
      );
      return null;
    } finally {
      setBusy(false);
    }
  };
  const robot = usePolling(api.robot, 1000);
  const step = plot?.step || 1,
    tutorial = !paused && (!plot?.completed || force);
  const point = plot?.points.find((p) => p.id === selected) || plot?.points[0];
  const begin = async () => {
    const p = plot || (await act("start"));
    if (p) await act("save", { step: 2 });
  };
  const finish = async (page: string) => {
    if (await act("complete")) {
      location.hash = page;
      location.reload();
    }
  };
  const edit = () => {
    setForce(true);
    setPaused(false);
    if (plot?.completed) void act("save", { step: 2 });
  };
  const diagnostics = technical && (
    <details className="diagnostics">
      <summary>Diagnóstico técnico</summary>
      <pre>{technical}</pre>
    </details>
  );
  if (!loaded)
    return (
      <main className="setup-shell" role="status">
        Preparando SEMI…
      </main>
    );
  if (initialError)
    return (
      <main className="setup-shell">
        <h1>SEMI</h1>
        <ErrorNotice message={error} />
        <button className="button primary" onClick={() => void load()}>
          Intentar de nuevo
        </button>
        <button
          className="button"
          onClick={() => {
            localStorage.removeItem("semi-plot");
            void load();
          }}
        >
          Volver a mi cafetal
        </button>
        {diagnostics}
      </main>
    );
  if (tutorial)
    return (
      <main className="setup-shell">
        <div className="setup-brand">
          <Leaf aria-hidden="true" />
          <strong>SEMI</strong>
          <ThemeSelector />
        </div>
        <p>
          Etapa {step} de 4 ·{" "}
          {plot?.demo ? "Recorrido de demostración" : "Mi cafetal"}
        </p>
        <progress value={step} max={4} aria-label="Avance de configuración" />
        <ErrorNotice message={error} />
        {busy && <p role="status">Guardando…</p>}
        {step === 1 && (
          <>
            <div className="robot-symbol" aria-hidden="true">
              <Bot size={76} />
            </div>
            <h1>Bienvenido a SEMI</h1>
            <p>
              Vamos a preparar tu cafetal para que puedas guardar y consultar
              las mediciones de tu suelo.
            </p>
            <p>Tú decides dónde medir y cómo conducir SEMI.</p>
            <button
              className="button primary"
              disabled={busy}
              onClick={() => void begin()}
            >
              Comenzar
            </button>
          </>
        )}
        {step === 2 && plot && (
          <>
            <h1>Mi cafetal</h1>
            <label>
              Nombre del cafetal
              <input
                value={name}
                maxLength={80}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ejemplo: Finca El Roble"
              />
            </label>
            <p>SEMI ya está preparado para el monitoreo de café arábica.</p>
            <details>
              <summary>Organizar mi cafetal por sectores</summary>
              <SectorManager
                plot={plot}
                busy={busy}
                act={async (a, d) => {
                  if (name !== plot.name && !(await act("save", { name })))
                    return null;
                  return act(a, d);
                }}
              />
            </details>
            <p>Puedes continuar sin crear sectores.</p>
          </>
        )}
        {step === 3 && plot && (
          <>
            <h1>Lugares para medir</h1>
            <PointEditor plot={plot} busy={busy} act={act} />
          </>
        )}
        {step === 4 && plot && (
          <>
            <h1>Comprobar y comenzar</h1>
            <section className="card">
              <h2>{plot.name}</h2>
              <p>
                {plot.zones.filter((z) => !z.archived).length} sectores ·{" "}
                {plot.points.length} lugares para medir
              </p>
              <Connection robot={robot.data} error={robot.error} />
              <p>
                Disponibilidad:{" "}
                {plot.points.some((p) => p.latest_sample)
                  ? "Ya hay mediciones de prueba guardadas."
                  : "Todavía no hay mediciones guardadas."}
              </p>
              <p>
                Los estados del vehículo y del suelo son simulados. No confirman
                hardware conectado.
              </p>
            </section>
            <details className="guided-reading" open>
              <summary>Tomar mi primera medición (opcional)</summary>
              <p>
                Con SEMI detenido, se colocaría la sonda siguiendo el
                procedimiento validado del equipo. Aquí guardaremos solo datos
                simulados.
              </p>
              {point ? (
                <>
                  <label>
                    Lugar para medir
                    <select
                      value={point.id}
                      onChange={(e) => setSelected(Number(e.target.value))}
                    >
                      {plot.points.map((p) => (
                        <option value={p.id} key={p.id}>
                          {p.name.split(" · T")[0]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="button primary"
                    disabled={
                      busy ||
                      robot.loading ||
                      !!robot.error ||
                      robot.data?.control.action !== "stop" ||
                      robot.data?.scenario !== "connected"
                    }
                    onClick={() => act("capture", { point: point.id })}
                  >
                    Guardar medición simulada
                  </button>
                  {point.latest_sample && (
                    <div className="card" role="status">
                      <h2>Resultado guardado en {point.code}</h2>
                      <p>
                        N {point.latest_sample.nitrogen ?? "—"} · P{" "}
                        {point.latest_sample.phosphorus ?? "—"} · K{" "}
                        {point.latest_sample.potassium ?? "—"}{" "}
                        {point.latest_sample.npk_unit}
                      </p>
                      <p>
                        Humedad {point.latest_sample.soil_moisture ?? "—"} % ·{" "}
                        {dateTime(point.latest_sample.captured_at)}
                      </p>
                      <p>
                        Datos simulados. No indican si el suelo es suficiente o
                        deficiente para el café. Puedes volver a verlos en Mis
                        mediciones.
                      </p>
                    </div>
                  )}
                </>
              ) : (
                <p>
                  Puedes volver para crear un lugar o comenzar sin tomar una
                  medición.
                </p>
              )}
            </details>
            <h2>¡Tu cafetal está listo!</h2>
            <div className="action-row">
              {[
                ["Ver mis mediciones", "data"],
                ["Controlar SEMI", "control"],
                ["Ir al inicio", "home"],
              ].map(([label, page]) => (
                <button
                  key={page}
                  className="button primary"
                  disabled={busy}
                  onClick={() => finish(page)}
                >
                  {label}
                </button>
              ))}
            </div>
          </>
        )}
        <div className="setup-actions">
          {step > 1 && (
            <button
              className="button"
              disabled={busy}
              onClick={() => act("save", { step: step - 1, name })}
            >
              Volver
            </button>
          )}
          {step > 1 && step < 4 && (
            <button
              className="button primary"
              disabled={busy || !name.trim()}
              onClick={() => act("save", { step: step + 1, name })}
            >
              Continuar
            </button>
          )}
          <button
            className="text-button"
            disabled={busy}
            onClick={() => setPaused(true)}
          >
            Salir por ahora
          </button>
        </div>
        {diagnostics}
      </main>
    );
  return (
    <>
      <div className="installation-tools">
        <strong>{plot?.name || "Mi cafetal"}</strong>
        <button className="button" onClick={edit}>
          {plot && !plot.completed
            ? "Continuar configuración"
            : "Configurar mi cafetal"}
        </button>
        <details className="session-tools">
          <summary>Demostración y ensayos</summary>
          <p>
            Cada recorrido crea un cafetal vacío de prueba. No borra tus
            mediciones.
          </p>
          <button
            className="button"
            disabled={busy}
            onClick={async () => {
              if (await act("demo")) {
                setForce(true);
                setPaused(false);
              }
            }}
          >
            Repetir bienvenida · demo aislada
          </button>
          {plot?.demo && (
            <>
              <button
                className="button"
                onClick={() => {
                  localStorage.removeItem("semi-plot");
                  location.reload();
                }}
              >
                Volver a mis datos
              </button>
              <TrialTools />
            </>
          )}
        </details>
        <ErrorNotice message={error} />
        {diagnostics}
      </div>
      <Dashboard plot={plot} act={act} setupBusy={busy} onConfigure={edit} />
    </>
  );
}
