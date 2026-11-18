import type { RobotStatus, Scan } from "../types/api";
export function deviceMessage(
  robot: RobotStatus | null,
  error?: string | null,
) {
  if (error) return "Sin conexión con el sistema";
  if (!robot) return "Conectando…";
  if (robot.manual?.traction.ready || robot.manual?.rack.ready)
    return "Robot conectado";
  const reasons: Record<string, string> = {
    integration_disabled: "Conexión del vehículo sin configurar",
    device_unregistered: "Vehículo sin registrar",
    device_disabled: "Conexión del vehículo deshabilitada",
    credential_missing: "Falta completar la conexión del vehículo",
    registered_waiting: "Vehículo registrado, esperando comunicación",
    session_waiting: "Esperando comunicación de la sesión actual",
    clock_invalid: "No pudimos confirmar la última comunicación",
    heartbeat_recent: "Robot conectado",
    telemetry_recent: "Robot conectado",
    disconnected: "Robot desconectado",
  };
  if (robot.diagnostics?.reason)
    return (
      reasons[robot.diagnostics.reason] || "Estado de conexión sin confirmar"
    );
  return robot.connection === "simulated_online"
    ? "Conectado · simulado"
    : robot.connection === "diagnostic_online"
      ? "Robot conectado"
      : robot.source === "real"
        ? "Vehículo no conectado"
        : "Desconectado · simulado";
}
export function lidarMessage(scan: Scan | null, expired = false) {
  if (!scan) return "No pudimos consultar el sensor de distancias";
  if (scan.acquisition?.state === "interrupted") return "Escaneo interrumpido";
  if (scan.acquisition?.state === "error") return "Error de lectura del sensor";
  if (expired || scan.status === "stale")
    return "No recibimos datos recientes del sensor";
  const states: Record<string, string> = {
    not_detected: "Sensor de distancias no detectado por USB",
    usb_unidentified: "Hay un adaptador USB por identificar",
    usb_detected: "Adaptador USB detectado. Falta iniciar el lector",
    waiting: "Sensor conectado, esperando datos",
    active: "Escaneo funcionando",
    interrupted: "Escaneo interrumpido",
    stale: "No recibimos datos recientes del sensor",
    error: "Error de lectura del sensor",
    unknown: "No pudimos comprobar la conexión USB",
  };
  if (scan.acquisition) return states[scan.acquisition.state] || states.unknown;
  return scan.valid
    ? "Escaneo funcionando"
    : scan.status === "error"
      ? "Error de lectura del sensor"
      : scan.status === "no_data"
        ? "Sensor conectado, esperando datos"
        : "Sensor de distancias desconectado";
}
