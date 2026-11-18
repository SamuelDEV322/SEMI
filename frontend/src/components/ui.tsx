import type { ReactNode } from "react";
import { Wifi, WifiOff, AlertTriangle, Clock3 } from "lucide-react";
import type { RobotStatus } from "../types/api";
export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={`card ${className}`}>
      {title && <h2>{title}</h2>}
      {children}
    </section>
  );
}
export function Connection({
  robot,
  error,
}: {
  robot: RobotStatus | null;
  error?: string | null;
}) {
  const diagnostic = robot?.connection === "diagnostic_online";
  const online = robot?.connection === "simulated_online" || diagnostic;
  return (
    <span className={`connection ${online ? "" : "offline"}`}>
      {online ? <Wifi size={14} /> : <WifiOff size={14} />}{" "}
      {error
        ? "Sin conexión con el sistema"
        : !robot
          ? "Conectando…"
          : diagnostic
            ? "Conexión establecida · diagnóstico"
            : online
              ? "Conectado · simulado"
              : robot.source === "real"
                ? "Vehículo no conectado"
                : "Desconectado · simulado"}
    </span>
  );
}
export function Empty({
  children = "Sin datos disponibles",
}: {
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      <span>—</span>
      <p>{children}</p>
    </div>
  );
}
export function ErrorNotice({ message }: { message: string | null }) {
  return message ? (
    <div className="notice danger" role="alert">
      <AlertTriangle size={18} />
      <span>{message}</span>
    </div>
  ) : null;
}
export function Reading({
  label,
  value,
  unit = "",
  note = "Demostración",
  stale = false,
}: {
  label: string;
  value: number | null | undefined;
  unit?: string;
  note?: string;
  stale?: boolean;
}) {
  return (
    <div className="reading">
      <span className="reading-label">{label}</span>
      <strong>
        {value == null
          ? "—"
          : new Intl.NumberFormat("es-CO", { maximumFractionDigits: 1 }).format(
              value,
            )}
        {value != null && <small> {unit}</small>}
      </strong>
      <span className={`reading-note ${stale ? "stale" : ""}`}>
        {stale && <Clock3 size={11} />}{" "}
        {value == null
          ? "No disponible"
          : stale
            ? `Dato obsoleto${note === "Demostración" ? " · demo" : ""}`
            : note}
      </span>
    </div>
  );
}
export const dateTime = (value: string) =>
  new Intl.DateTimeFormat("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(value));
