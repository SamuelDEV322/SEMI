import { soilMessage } from "../components/SoilReadings";
import { mechanism } from "../services/manual";
import { deviceMessage, lidarMessage } from "../services/sourceStatus";
import { useScanFreshness } from "../hooks/useScanFreshness";
import { DeviceReadings } from "../components/DeviceReadings";
import { useRuntime } from "../Runtime";
import { Check } from "lucide-react";
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
  const rows = [
    ["Conexión", deviceMessage(robot)],
    ["Movimiento", demo ? "Demostración" : mechanism(robot?.manual?.traction)],
    ["Módulo agrícola", demo ? "Demostración" : mechanism(robot?.manual?.rack)],
    ["Sensor de humedad", demo ? "Demostración" : soilMessage(robot)],
    ["LiDAR", lidarMessage(scan, expired)],
    ["Nitrógeno", "Simulado"],
    ["Potasio", "Simulado"],
  ];
  return (
    <div className="page-stack">
      <Card title="Estado del robot">
        <div className="status-list">
          {rows.map(([name, status]) => (
            <div key={name}>
              <span>{name}</span>
              <small>{status}</small>
            </div>
          ))}
        </div>
      </Card>
      <DeviceReadings robot={robot} />
      {(runtime.dev_tools || !demo) && (
        <details className="diagnostics">
          <summary>Detalles del sistema</summary>
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
    </div>
  );
}
