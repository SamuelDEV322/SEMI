import { deviceMessage, lidarMessage } from "../services/sourceStatus";
import { useScanFreshness } from "../hooks/useScanFreshness";
import { DeviceReadings } from "../components/DeviceReadings";
import { useRuntime } from "../Runtime";
import { AlertTriangle, Info, Check, Radio } from "lucide-react";
import type { RobotStatus, Scan } from "../types/api";
import { Card } from "../components/ui";
export function Status({
  robot,
  scan,
}: {
  robot: RobotStatus | null;
  scan: Scan | null;
}) {
  const runtime = useRuntime();
  const demo = runtime.mode === "demonstration";
  const expired = useScanFreshness(scan);
  const soil = robot?.telemetry.device_reading?.sensors.soil_moisture_adc;
  const soilStatus =
    !soil || soil.status === "unavailable"
      ? "Sin lecturas recibidas del sensor de suelo"
      : soil.status !== "valid"
        ? "No se pudo obtener una lectura válida"
        : robot?.telemetry.device_reading?.freshness === "stale"
          ? "Lectura sin calibrar · desactualizada"
          : "Lectura recibida · sin calibrar";
  const rows = [
    [
      "Locomoción",
      demo
        ? "Demostración · movimiento físico no disponible"
        : robot?.connection === "diagnostic_online"
          ? "Conexión de diagnóstico · movimiento no disponible"
          : "Movimiento físico no disponible",
    ],
    [
      "Humedad del suelo",
      demo ? "Demostración · sensor de suelo no conectado" : soilStatus,
    ],
    [
      "Sensor NPK",
      demo
        ? "Demostración · sensor de suelo no conectado"
        : "Sin lecturas NPK recibidas",
    ],
    ["RPLidar A1", lidarMessage(scan, expired)],

    ["Ambiente e inclinación", "No confirmados · no disponibles"],
  ];
  return (
    <div className="page-stack">
      <DeviceReadings robot={robot} />
      <Card title="Estado de componentes">
        <p className="caption mb-3">
          {demo
            ? "Suelo y locomoción en demostración. La percepción indica su propia fuente."
            : "La disponibilidad se muestra por componente. Un sensor de distancias activo no confirma la conexión del vehículo."}
        </p>
        <div className="status-list">
          {rows.map(([name, status]) => (
            <div key={name}>
              <span>{name}</span>
              <small>{status}</small>
            </div>
          ))}
        </div>
      </Card>
      {(runtime.dev_tools || !demo) && (
        <details className="diagnostics">
          <summary>Diagnóstico técnico</summary>
          <pre>
            {JSON.stringify(
              {
                source: scan?.source,
                status: scan?.status,
                age_ms: scan?.age_ms,
                error: scan?.error,
                acquisition: scan?.acquisition,
                vehicle: robot?.diagnostics,
              },
              null,
              2,
            )}
          </pre>
        </details>
      )}
      <Card title="Sensor de distancias">
        <p>
          {scan?.source === "real"
            ? "Fuente configurada: USB"
            : "Lecturas de prueba"}
        </p>
        <p>{lidarMessage(scan, expired)}</p>
        <p className="caption">
          Muestra distancias alrededor del sensor. No identifica materiales del
          suelo.
        </p>
      </Card>
      <Card title="Conexión">
        <div className="connection-info">
          <Radio size={22} />
          <div>
            <strong>{deviceMessage(robot)}</strong>
            <p className="caption">
              {demo
                ? "Red local · control de demostración · no requiere Internet"
                : "Red local · no requiere Internet"}
            </p>
          </div>
        </div>
      </Card>
      <Card title="Mantenimiento preventivo">
        <p className="caption">
          Lista manual; no es un diagnóstico automático.
        </p>
        <div className="maintenance">
          {[
            "Inspeccionar orugas, ruedas y fijaciones",
            "Revisar cubierta y ventana del LiDAR",
            "Limpiar sonda y módulo agrícola",
            "Revisar cableado con el equipo desenergizado",
          ].map((text) => (
            <label key={text}>
              <input type="checkbox" />
              <span>{text}</span>
              <Check size={15} />
            </label>
          ))}
        </div>
        <p className="caption">
          Las marcas son locales a esta vista y no constituyen un historial.
        </p>
      </Card>
      <Card title="Alertas y bloqueos">
        <div className="notice danger">
          <AlertTriangle size={19} />
          <span>
            Movimiento físico no disponible. La revisión técnica está pendiente.
          </span>
        </div>
        {demo && robot?.scenario === "disconnected" && (
          <div className="notice danger">
            Pérdida del enlace simulada. No se permiten órdenes de movimiento.
          </div>
        )}
        {robot?.scenario === "stale" && (
          <div className="notice">Datos actuales marcados como obsoletos.</div>
        )}
        <div className="notice">
          <Info size={18} />
          <span>
            {demo
              ? "La conexión inalámbrica del sensor está pendiente de validar. USB está preparado para diagnóstico con inicio manual."
              : "El lector del sensor se inicia desde el equipo de conexión. La aplicación no lo activa automáticamente."}
          </span>
        </div>
      </Card>
    </div>
  );
}
