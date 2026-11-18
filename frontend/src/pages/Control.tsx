import { useRef } from "react";
import {
  ArrowUp,
  ArrowDown,
  ArrowLeft,
  ArrowRight,
  Square,
  LogOut,
} from "lucide-react";
import type { Action, RobotStatus, Scan } from "../types/api";
import { useManualControl } from "../hooks/useManualControl";
import { LidarRadar } from "../components/LidarRadar";
import { ThemeSelector } from "../components/ThemeSelector";
import { useRuntime } from "../Runtime";
export function Control({
  robot,
  scan,
  online,
  onExit,
  scanError,
}: {
  robot: RobotStatus | null;
  scan: Scan | null;
  online: boolean;
  onExit: () => void;
  scanError: string | null;
}) {
  const runtime = useRuntime();
  const demo = runtime.mode === "demonstration";
  const c = useManualControl(robot, online),
    pointer = useRef<number | null>(null);
  const directions: { action: Action; label: string; icon: typeof ArrowUp }[] =
    [
      { action: "forward", label: "Adelante", icon: ArrowUp },
      { action: "left", label: "Izquierda", icon: ArrowLeft },
      { action: "right", label: "Derecha", icon: ArrowRight },
      { action: "backward", label: "Atrás", icon: ArrowDown },
    ];
  const leave = async () => {
    if (online) await c.stop();
    onExit();
  };
  const confirmed = !demo
    ? "Estado del vehículo sin confirmar"
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
                onPointerDown={(e) => {
                  if (e.button !== 0 || pointer.current !== null) return;
                  pointer.current = e.pointerId;
                  e.currentTarget.setPointerCapture(e.pointerId);
                  c.start(action);
                }}
                onPointerUp={(e) => {
                  if (pointer.current === e.pointerId) {
                    pointer.current = null;
                    c.release();
                  }
                }}
                onPointerCancel={() => {
                  pointer.current = null;
                  c.release();
                }}
                onLostPointerCapture={() => {
                  pointer.current = null;
                  c.release();
                }}
                onBlur={c.release}
                onKeyDown={(e) => {
                  if ([" ", "Enter"].includes(e.key) && !e.repeat) {
                    e.preventDefault();
                    c.start(action);
                  }
                }}
                onKeyUp={(e) => {
                  if ([" ", "Enter"].includes(e.key)) {
                    e.preventDefault();
                    c.release();
                  }
                }}
              >
                <Icon size={22} />
                <span>{label}</span>
              </button>
            ))}
          </div>
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
            disabled={!online}
            onClick={() => void c.stop()}
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
                  command: c.action,
                  confirmed: robot?.control.action,
                  scanError,
                  error: c.technicalError,
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
