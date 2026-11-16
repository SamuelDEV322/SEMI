import { ArrowRight, BatteryMedium, Activity } from "lucide-react";
import type { RobotStatus, Sample } from "../types/api";
import { Card, Reading, Empty, dateTime } from "../components/ui";
export function Home({
  robot,
  latest,
  onNavigate,
}: {
  robot: RobotStatus | null;
  latest: Sample | null;
  onNavigate: (page: string) => void;
}) {
  const battery = robot?.telemetry.battery;
  return (
    <div className="page-stack">
      <Card title="Estado del robot" className="robot-summary">
        <div className="summary-status">
          <Activity size={16} />
          {!robot
            ? "Estado del vehículo sin confirmar"
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
          Estimación simulada ·{" "}
          {battery?.freshness === "stale"
            ? "dato obsoleto"
            : "sin batería física conectada"}
        </p>
      </Card>
      <section>
        <div className="section-heading">
          <h2>Mediciones principales</h2>
          <span>DATOS DE PRUEBA</span>
        </div>
        <div className="reading-grid three">
          <Reading
            label="Humedad del suelo"
            value={latest?.status === "valid" ? latest.soil_moisture : null}
            unit="%"
            stale={latest?.freshness === "stale"}
          />
          <Reading
            label="Nitrógeno"
            value={latest?.status === "valid" ? latest.nitrogen : null}
            unit="mg/kg"
            stale={latest?.freshness === "stale"}
          />
          <Reading
            label="Potasio"
            value={latest?.status === "valid" ? latest.potassium : null}
            unit="mg/kg"
            stale={latest?.freshness === "stale"}
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
                    {event.kind === "control"
                      ? "Control manual en demostración"
                      : event.kind === "sample"
                        ? "Medición simulada guardada"
                        : event.kind === "scenario"
                          ? "Cambio del estado de demostración"
                          : "Actividad registrada"}
                  </p>
                  <small>{dateTime(event.created_at)} · demostración</small>
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
        SEMI acompaña tus decisiones. Control y suelo en demostración. Consulta
        la fuente del sensor de distancias en Estado.
      </p>
    </div>
  );
}
