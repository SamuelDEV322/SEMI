import { ArrowRight, BatteryMedium, Activity } from "lucide-react";
import type { RobotStatus, Sample } from "../types/api";
import { Card, Reading, Empty, dateTime } from "../components/ui";
import { useRuntime } from "../Runtime";
export function Home({
  robot,
  latest,
  onNavigate,
}: {
  robot: RobotStatus | null;
  latest: Sample | null;
  onNavigate: (page: string) => void;
}) {
  const demo = useRuntime().mode === "demonstration";
  const battery = robot?.telemetry.battery;
  return (
    <div className="page-stack">
      <Card title="Estado del robot" className="robot-summary">
        <div className="summary-status">
          <Activity size={16} />
          {!robot || robot.state === "unavailable"
            ? "Estado del vehículo sin confirmar"
            : robot.state === "diagnostic"
              ? "Conexión establecida · pruebas sin movimiento"
              : robot.state === "moving_simulated"
                ? "Movimiento simulado"
                : robot?.state === "fault"
                  ? "Fallo simulado"
                  : "Detenido · simulación"}
        </div>
        <div className="battery-summary">
          <BatteryMedium size={27} />
          <strong>
            Batería {battery?.value == null ? "—" : `${battery.value} %`}
          </strong>
        </div>
        <p className="caption">
          {demo ? "Estimación simulada · " : "Carga no disponible · "}
          {battery?.freshness === "stale"
            ? "dato obsoleto"
            : "sin medición física de batería"}
        </p>
      </Card>
      <section>
        <div className="section-heading">
          <h2>Mediciones principales</h2>
          <span>{demo ? "DATOS DE PRUEBA" : "LECTURAS DEL SUELO"}</span>
        </div>
        <div className="reading-grid three">
          <Reading
            label="Humedad del suelo"
            value={latest?.status === "valid" ? latest.soil_moisture : null}
            unit="%"
            stale={latest?.freshness === "stale"}
            note={
              latest?.source === "real" ? "Lectura del sensor" : "Demostración"
            }
          />
          <Reading
            label="Nitrógeno"
            value={latest?.status === "valid" ? latest.nitrogen : null}
            unit={latest?.npk_unit || ""}
            stale={latest?.freshness === "stale"}
            note={
              latest?.source === "real" ? "Lectura del sensor" : "Demostración"
            }
          />
          <Reading
            label="Potasio"
            value={latest?.status === "valid" ? latest.potassium : null}
            unit={latest?.npk_unit || ""}
            stale={latest?.freshness === "stale"}
            note={
              latest?.source === "real" ? "Lectura del sensor" : "Demostración"
            }
          />
        </div>
      </section>
      <button
        className="button primary wide"
        onClick={() => onNavigate("control")}
      >
        Ir al control <ArrowRight size={18} />
      </button>
      <Card title="Actividad reciente">
        {!robot ? (
          <p>No pudimos consultar la actividad. Comprueba la conexión.</p>
        ) : robot.events.length ? (
          <ul className="activity-list">
            {robot.events.slice(0, 4).map((event) => (
              <li key={event.id}>
                <span className="activity-dot" />
                <div>
                  <p>
                    {event.source === "real"
                      ? "Actividad registrada"
                      : event.kind === "control"
                        ? "Control manual en demostración"
                        : event.kind === "sample"
                          ? "Medición simulada guardada"
                          : event.kind === "scenario"
                            ? "Cambio del estado de demostración"
                            : "Actividad registrada"}
                  </p>
                  <small>
                    {dateTime(event.created_at)}
                    {event.source === "real" ? "" : " · demostración"}
                  </small>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <Empty>Sin actividad registrada</Empty>
        )}
        <button className="text-button" onClick={() => onNavigate("data")}>
          Consultar mediciones <ArrowRight size={15} />
        </button>
      </Card>
      <p className="footnote">
        {demo
          ? "SEMI acompaña tus decisiones. Control y suelo en demostración. Consulta la fuente del sensor de distancias en Estado."
          : "SEMI acompaña tus decisiones. Conecta los sensores para consultar lecturas de tu cafetal."}
      </p>
    </div>
  );
}
