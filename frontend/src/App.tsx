import { useState } from "react";
import {
  Home as HomeIcon,
  Gamepad2,
  ChartNoAxesCombined,
  Wrench,
  Leaf,
  FlaskConical,
  ChevronDown,
} from "lucide-react";
import { api } from "./services/api";
import { usePolling } from "./hooks/usePolling";
import { Home } from "./pages/Home";
import { Control } from "./pages/Control";
import { Data } from "./pages/Data";
import { Status } from "./pages/Status";
import { ThemeSelector } from "./components/ThemeSelector";
import { Connection, ErrorNotice } from "./components/ui";
import type { Scenario } from "./types/api";
import type { SetupAction, SetupPlot } from "./types/setup";
import { useRuntime } from "./Runtime";
const tabs = [
  {
    id: "home",
    label: "Inicio",
    icon: HomeIcon,
    title: "SEMI",
    subtitle: "Monitoreo agrícola",
  },
  {
    id: "control",
    label: "Control",
    icon: Gamepad2,
    title: "Control de SEMI",
    subtitle: "Mantén un mando para conducir",
  },
  {
    id: "data",
    label: "Datos",
    icon: ChartNoAxesCombined,
    title: "Mediciones del cultivo",
    subtitle: "Tus lugares, resultados e historial",
  },
  {
    id: "status",
    label: "Estado",
    icon: Wrench,
    title: "Estado y mantenimiento",
    subtitle: "Fuentes, componentes y cuidado del equipo",
  },
];
function initialPage() {
  const hash = window.location.hash.slice(1);
  return tabs.some((t) => t.id === hash) ? hash : "home";
}
export function Dashboard({
  plot,
  act,
  setupBusy,
  onConfigure,
}: {
  plot: SetupPlot | null;
  act: SetupAction;
  setupBusy: boolean;
  onConfigure: () => void;
}) {
  const runtime = useRuntime();
  const [page, setPage] = useState(initialPage),
    [scenarioError, setScenarioError] = useState<string | null>(null),
    [switching, setSwitching] = useState(false);
  const robot = usePolling(api.robot, 500),
    latest = usePolling(api.latest, 2500),
    history = usePolling(api.history, 5000),
    scan = usePolling(api.lidar, 1000),
    points = usePolling(api.points, 3000);
  const tab = tabs.find((t) => t.id === page)!;
  const navigate = (next: string) => {
    setPage(next);
    window.history.replaceState(null, "", `#${next}`);
    window.scrollTo({ top: 0, behavior: "instant" });
  };
  const refresh = () => {
    robot.refresh();
    latest.refresh();
    history.refresh();
    scan.refresh();
    points.refresh();
  };
  const setScenario = async (value: Scenario) => {
    setSwitching(true);
    setScenarioError(null);
    try {
      await api.scenario(value);
      refresh();
    } catch (e) {
      setScenarioError(e instanceof Error ? e.message : "Error de escenario");
    } finally {
      setSwitching(false);
    }
  };
  return (
    <div className={`app-shell ${page === "control" ? "control-mode" : ""}`}>
      <aside className="desktop-brand">
        <div className="brand-mark">
          <Leaf size={28} />
        </div>
        <strong>SEMI</strong>
        <span>
          Sistema Eficiente de
          <br />
          Monitoreo Inteligente
        </span>
        <p>Una herramienta para acompañar el cuidado de tu cultivo.</p>
        <small>SEMI · SOFTWARE LOCAL</small>
      </aside>
      <div className="app-main">
        {runtime.mode === "demonstration" && (
          <div className="demo-banner">
            <FlaskConical size={15} />
            <strong>MODO DEMOSTRACIÓN</strong>
            <span>Control y suelo simulados</span>
          </div>
        )}
        <div className="theme-bar">
          <ThemeSelector />
        </div>
        <header className="page-header">
          <div>
            <h1>{tab.title}</h1>
            <p>{tab.subtitle}</p>
          </div>
          {page === "home" && (
            <div className="header-leaf">
              <Leaf size={24} />
            </div>
          )}
        </header>
        <div className="connection-line">
          <Connection robot={robot.data} error={robot.error} />
        </div>
        {runtime.dev_tools && (
          <details className="demo-tools">
            <summary>
              Escenarios de demostración <ChevronDown size={14} />
            </summary>
            <label>
              Estado simulado
              <select
                aria-label="Escenario de demostración"
                disabled={switching}
                value={robot.data?.scenario || "connected"}
                onChange={(e) => void setScenario(e.target.value as Scenario)}
              >
                <option value="connected">Conectado · demo</option>
                <option value="disconnected">Desconexión simulada</option>
                <option value="no_data">Sin datos actuales</option>
                <option value="stale">Datos obsoletos</option>
                <option value="error">Error de adquisición</option>
              </select>
            </label>
            <p>
              Los cambios solo afectan las fuentes de prueba. No se conectan
              dispositivos.
            </p>
          </details>
        )}
        <main>
          {page !== "control" && page !== "data" && (
            <ErrorNotice
              message={
                robot.error ? "No hay conexión con el sistema." : scenarioError
              }
            />
          )}
          {robot.loading ? (
            <div className="loading" role="status">
              <span className="spinner" />
              Cargando SEMI…
            </div>
          ) : (
            <>
              {page === "home" && (
                <>
                  <ErrorNotice
                    message={
                      latest.error
                        ? "No se pudo obtener la última medición."
                        : null
                    }
                  />
                  <Home
                    robot={robot.data}
                    latest={latest.data}
                    onNavigate={navigate}
                  />
                </>
              )}
              {page === "control" && (
                <>
                  <Control
                    serviceAvailable={!robot.error && !switching}
                    robot={robot.data}
                    scan={scan.data}
                    scanError={scan.error}
                    onExit={() => navigate("home")}
                    online={
                      !!robot.data?.capabilities.manual_control &&
                      robot.data?.connection === "simulated_online" &&
                      !robot.error &&
                      !switching
                    }
                  />
                </>
              )}
              {page === "data" && (
                <Data
                  plot={plot}
                  act={act}
                  setupBusy={setupBusy}
                  onConfigure={onConfigure}
                  samples={history.data || []}
                  points={points.data || []}
                  pointsLoading={points.loading}
                  historyError={history.error}
                  pointsError={points.error}
                  onRefresh={refresh}
                />
              )}
              {page === "status" && (
                <>
                  <ErrorNotice
                    message={
                      scan.error
                        ? "No se pudo obtener información del sensor de distancias."
                        : null
                    }
                  />
                  <Status robot={robot.data} scan={scan.data} />
                </>
              )}
            </>
          )}
        </main>
        <nav className="bottom-nav" aria-label="Navegación principal">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => navigate(id)}
              aria-current={page === id ? "page" : undefined}
            >
              <span>
                <Icon size={21} />
              </span>
              {label}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}
