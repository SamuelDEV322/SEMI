import { useState } from "react";
import { api } from "../services/api";
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
  const [sourceError, setSourceError] = useState<string | null>(null);
  const rows = [
    ["Locomoción", "Demostración · movimiento físico no disponible"],
    ["Humedad del suelo", "Demostración · sensor de suelo no conectado"],
    ["Sensor NPK", "Demostración · sensor de suelo no conectado"],
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
      <Card title="Energía y batería">
        <Reading
          label="Carga estimada"
          value={robot?.telemetry.battery.value}
          unit="%"
          stale={robot?.telemetry.battery.freshness === "stale"}
        />
        <p className="caption">
          Carga simulada. La batería física todavía no se supervisa.
        </p>
      </Card>
      <Card title="Estado de componentes">
        <p className="caption mb-3">
          Suelo y locomoción en demostración. La percepción indica su propia
          fuente.
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
      <details className="diagnostics">
        <summary>Diagnóstico técnico</summary>
        <Card title="Fuente del sensor de distancias">
          <label>
            Origen de la percepción
            <select
              aria-label="Origen LiDAR"
              value={scan?.source || "mock"}
              onChange={async (e) => {
                setSourceError(null);
                try {
                  await api.lidarSource(e.target.value);
                } catch (error) {
                  setSourceError(
                    error instanceof Error
                      ? error.message
                      : "No se pudo cambiar la fuente.",
                  );
                }
              }}
            >
              <option value="mock">Demostración</option>
              <option value="replay">Reproducción de prueba</option>
              <option value="real">Sensor USB (diagnóstico)</option>
            </select>
          </label>
          <p role="status">{sourceError}</p>
          <p className="caption">
            La fuente USB requiere habilitación local y un lector iniciado con
            confirmación. Esta pantalla nunca abre puertos. Cambiar de fuente no
            apaga el lector USB; ciérralo con Ctrl+C en su terminal.
          </p>
          <details>
            <summary>Diagnóstico LiDAR y locomoción</summary>
            <p>
              Locomoción: verificar driver, corrientes, batería, reguladores,
              pines, habilitación y parada física antes de integrar.
            </p>
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
        </Card>
      </details>
      <Card title="Conexión">
        <div className="connection-info">
          <Radio size={22} />
          <div>
            <strong>
              {robot?.connection === "simulated_online"
                ? "Enlace simulado activo"
                : "Enlace no disponible"}
            </strong>
            <p className="caption">
              Red local · control de demostración · no requiere Internet
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
        {robot?.scenario === "disconnected" && (
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
            La conexión inalámbrica del sensor está pendiente de validar. USB
            está preparado para diagnóstico con inicio manual.
          </span>
        </div>
      </Card>
    </div>
  );
}
