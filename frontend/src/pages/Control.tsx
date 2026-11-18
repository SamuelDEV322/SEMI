import {
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Square,
  LogOut,
} from "lucide-react";
import type { Action, RobotStatus, Scan } from "../types/api";
import { useRackControl } from "../hooks/useRackControl";
import { useManualControl } from "../hooks/useManualControl";
import { LidarRadar } from "../components/LidarRadar";
import { ThemeSelector } from "../components/ThemeSelector";
import { useRuntime } from "../Runtime";
export function Control({
  serviceAvailable,
  robot,
  scan,
  online,
  onExit,
  scanError,
}: {
  serviceAvailable: boolean;
  robot: RobotStatus | null;
  scan: Scan | null;
  online: boolean;
  onExit: () => void;
  scanError: string | null;
}) {
  const runtime = useRuntime();
  const demo = runtime.mode === "demonstration";
  const c = useManualControl(robot, online);
  const rackOnline =
    demo &&
    serviceAvailable &&
    !!robot?.rack?.available &&
    robot.rack.connection === "simulated_online";
  const r = useRackControl(robot?.rack, rackOnline);
  const stopAll = async () => {
    r.cancel();
    await c.stopAll();
  };
  const rackState = !rackOnline
    ? robot?.rack?.state === "error"
      ? "Error del módulo"
      : demo
        ? "No disponible"
        : "No habilitado"
    : r.pendingStop
      ? "Parada solicitada…"
      : r.technicalError
        ? "Sin confirmación"
        : robot?.rack?.state === "raising_simulated"
          ? "Subiendo (simulado)"
          : robot?.rack?.state === "lowering_simulated"
            ? "Bajando (simulado)"
            : r.action !== "stop"
              ? "Solicitud en curso…"
              : "Detenido (simulado)";
  const directions: {
    action: Exclude<Action, "stop">;
    label: string;
    icon: typeof ArrowUp;
  }[] = [
    { action: "forward", label: "Adelante", icon: ArrowUp },
    { action: "left", label: "Izquierda", icon: ArrowLeft },
    { action: "right", label: "Derecha", icon: ArrowRight },
    { action: "backward", label: "Atrás", icon: ArrowDown },
  ];
  const leave = async () => {
    if (demo) await stopAll();
    onExit();
  };
  const confirmed = !demo
    ? "Tracción física no habilitada"
    : robot?.surface_trial?.blocked
      ? "Ensayo: STOP simulado"
      : robot?.control.action === "stop"
        ? "Detenido en simulación"
        : robot
          ? "Movimiento en simulación"
          : "Sin confirmación";
  return (
    <section className="drive-screen" aria-label="Control de SEMI">
      <header className="drive-top">
        <button
          className="button exit-drive"
          onClick={() => void leave()}
          aria-label="Salir del control"
        >
          <LogOut size={18} />
          Salir
        </button>
        <strong>SEMI</strong>
        <span
          className={`drive-connection ${online || robot?.connection === "diagnostic_online" ? "" : "offline"}`}
        >
          {robot?.connection === "diagnostic_online"
            ? "● Diagnóstico"
            : online
              ? "● Conectado · demo"
              : "○ Sin conexión"}
        </span>
        <ThemeSelector />
      </header>
      <div className="drive-status" role="status">
        {c.pendingStop ? "Parada solicitada…" : confirmed}
        <span>{demo ? "SOLO DEMOSTRACIÓN" : "CONTROL NO DISPONIBLE"}</span>
      </div>
      <div className="drive-content">
        <div className="drive-perception">
          <LidarRadar scan={scanError ? null : scan} />
          {scanError && (
            <p className="caption" role="alert">
              No se pudo obtener el escaneo. Comprueba la conexión del sensor.
            </p>
          )}
        </div>
        <div className="drive-commands">
          <p className="hold-help">
            Mantén pulsado para mover. Suelta para detener.
          </p>
          <div className="dpad">
            <span className="dpad-center" aria-live="polite">
              {c.action === "stop" ? "SIN MANDO" : "MANDO ACTIVO"}
            </span>
            {directions.map(({ action, label, icon: Icon }) => (
              <button
                key={action}
                aria-label={label}
                aria-pressed={c.action === action}
                disabled={!online || c.pendingStop}
                className={`direction ${action} ${c.action === action ? "pressed" : ""}`}
                {...c.bind(action)}
              >
                <Icon size={22} />
                <span>{label}</span>
              </button>
            ))}
          </div>
          <section className="rack-controls" aria-label="Módulo agrícola">
            <div className="rack-heading">
              <strong>Módulo agrícola</strong>
              <span role="status">{rackState}</span>
            </div>
            <div className="rack-buttons">
              <button
                className={`button ${r.action === "up" ? "pressed" : ""}`}
                disabled={!rackOnline || r.pendingStop || c.pendingStop}
                aria-pressed={r.action === "up"}
                {...r.bind("up")}
              >
                <ArrowUp size={18} /> Subir
              </button>
              <button
                className={`button ${r.action === "down" ? "pressed" : ""}`}
                disabled={!rackOnline || r.pendingStop || c.pendingStop}
                aria-pressed={r.action === "down"}
                {...r.bind("down")}
              >
                <ArrowDown size={18} /> Bajar
              </button>
            </div>
          </section>
          <div className="speed-row">
            <span>Velocidad</span>
            <div className="segmented">
              <button
                disabled={!online}
                aria-pressed={c.speed === "low"}
                onClick={() => c.setSpeed("low")}
              >
                Baja
              </button>
              <button
                disabled={!online}
                aria-pressed={c.speed === "medium"}
                onClick={() => c.setSpeed("medium")}
              >
                Media
              </button>
            </div>
          </div>
          <button
            className="button stop-button wide"
            disabled={!demo || !serviceAvailable}
            onPointerDown={(event) => {
              if (event.button !== 0) return;
              event.preventDefault();
              void stopAll();
            }}
            onClick={(event) => {
              if (event.detail === 0) void stopAll();
            }}
          >
            <Square size={18} fill="currentColor" />
            {c.pendingStop ? "SOLICITANDO PARADA…" : "DETENER ROBOT"}
          </button>
          <p className="drive-feedback" role="status">
            {c.message}
          </p>
        </div>
      </div>
      <footer className="drive-footer">
        {demo
          ? "Sin movimiento físico · Parada web, no emergencia física."
          : "El control físico todavía no está habilitado."}
        {runtime.dev_tools && (
          <details className="drive-diagnostics">
            <summary>Diagnóstico</summary>
            <pre>
              {JSON.stringify(
                {
                  traction: {
                    intent: c.action,
                    confirmed: robot?.control,
                    error: c.technicalError,
                  },
                  rack: {
                    intent: r.action,
                    confirmed: robot?.rack,
                    error: r.technicalError,
                    message: r.message,
                  },
                  lidar: {
                    source: scan?.source,
                    status: scan?.status,
                    freshness: scan?.freshness,
                    error: scanError || scan?.error,
                  },
                  hardwareActed: false,
                },
                null,
                2,
              )}
            </pre>
          </details>
        )}
      </footer>
    </section>
  );
}
