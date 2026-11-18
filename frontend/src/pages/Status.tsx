import { DeviceReadings } from "../components/DeviceReadings";
import { useRuntime } from "../Runtime";
import { AlertTriangle, Info, Check, Radio } from "lucide-react";
import type { RobotStatus, Scan } from "../types/api";
import { Card, Reading } from "../components/ui";
export function Status({
  robot,
  scan,
}: {
  robot: RobotStatus | null;
  scan: Scan | null;
}) {
  const runtime = useRuntime();
  const demo = runtime.mode === "demonstration";
  const soil = robot?.telemetry.device_reading?.sensors.soil_moisture_adc;
  const soilStatus =
    !soil || soil.status === "unavailable"
      ? "Sensor de suelo no disponible"
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
          : "Vehículo no conectado · control no disponible",
    ],
    [
      "Humedad del suelo",
      demo
        ? "Demostración · sensor de suelo no conectado"
        : soil
          ? soilStatus
          : "Sensor de suelo no conectado",
    ],
    [
      "Sensor NPK",
      demo
        ? "Demostración · sensor de suelo no conectado"
        : "Sensor de suelo no conectado",
    ],
    [
      "RPLidar A1",
      scan?.valid
        ? "Escaneo disponible · consulta la fuente"
        : "Sin escaneo actual",
    ],
    ["Cámara", "No confirmada · no disponible"],
    ["Ambiente e inclinación", "No confirmados · no disponibles"],
  ];
  return (
    <div className="page-stack">
      <DeviceReadings robot={robot} />
      <Card title="Energía y batería">
        <Reading
          label="Carga estimada"
          value={robot?.telemetry.battery.value}
          unit="%"
          stale={robot?.telemetry.battery.freshness === "stale"}
          note={demo ? "Demostración" : "Lectura del sensor"}
        />
        <p className="caption">
          {demo
            ? "Carga simulada. La batería física todavía no se supervisa."
            : "Todavía no se recibe una medición de la batería."}
        </p>
      </Card>
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
      {runtime.dev_tools && (
        <details className="diagnostics">
          <summary>Diagnóstico técnico</summary>
          <pre>
            {JSON.stringify(
              {
                source: scan?.source,
                status: scan?.status,
                age_ms: scan?.age_ms,
                error: scan?.error,
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
            ? "RPLidar A1 · lectura USB"
            : "Lecturas de prueba"}
        </p>
        <p>
          {scan?.status === "stale"
            ? "Última lectura desactualizada"
            : scan?.status === "error"
              ? "No pudimos obtener las distancias"
              : scan?.valid
                ? "Lecturas disponibles"
                : scan?.status === "no_data"
                  ? "Sensor sin lecturas"
                  : "Sensor no conectado"}
        </p>
        <p className="caption">
          Muestra distancias alrededor del sensor. No identifica materiales del
          suelo.
        </p>
      </Card>
      <Card title="Conexión">
        <div className="connection-info">
          <Radio size={22} />
          <div>
            <strong>
              {robot?.connection === "simulated_online"
                ? "Enlace simulado activo"
                : robot?.connection === "diagnostic_online"
                  ? "Conexión establecida · diagnóstico"
                  : "Enlace no disponible"}
            </strong>
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
