import { useCallback, useState } from "react";
import { usePolling } from "../hooks/usePolling";
import { request, post } from "../services/api";
import { Card, dateTime } from "./ui";

interface Row {
  id: number;
  source: "real";
  plot: string;
  point: string | null;
  received_at: string;
  adc: { value: number | null; status: string };
}
export function AdcHistory({
  point,
  pointName,
  plotId,
}: {
  point?: number;
  pointName?: string;
  plotId: number;
}) {
  const [onlyPoint, setOnlyPoint] = useState(false);
  const [feedback, setFeedback] = useState("");
  const fetchRows = useCallback(
    () =>
      request<Row[]>(
        "measurements/adc/?limit=30" +
          (onlyPoint && point ? "&point=" + point : ""),
      ),
    [point, onlyPoint, plotId],
  );
  const history = usePolling(fetchRows, 5000);
  async function assign(id: number) {
    try {
      await post("measurements/adc/", { reading: id, point });
      setFeedback("Lectura asociada a " + pointName + ".");
      history.refresh();
    } catch (error) {
      setFeedback(String(error));
    }
  }
  return (
    <Card title="Historial del sensor de humedad">
      <p className="caption">
        Lecturas del ESP32 en este cafetal, pendientes de calibración.
      </p>
      {point && (
        <label>
          <input
            type="checkbox"
            checked={onlyPoint}
            onChange={(e) => setOnlyPoint(e.target.checked)}
          />{" "}
          Solo el lugar seleccionado
        </label>
      )}
      {feedback && <p role="status">{feedback}</p>}
      {history.error ? (
        <p role="alert">No pudimos consultar las lecturas.</p>
      ) : history.loading ? (
        <p>Cargando lecturas…</p>
      ) : history.data?.length ? (
        <ul className="activity-list">
          {history.data.map((row) => (
            <li key={row.id}>
              <div>
                <strong>{row.adc.value ?? "—"} ADC</strong> ·{" "}
                {row.point || "Sin punto asignado"}
                <small>
                  {dateTime(row.received_at)} ·{" "}
                  {row.adc.value === 0 || row.adc.status !== "valid"
                    ? "Revisar sensor"
                    : "Lectura real"}
                </small>
                {!row.point && point && (
                  <button
                    className="text-button"
                    onClick={() => void assign(row.id)}
                  >
                    Asociar a {pointName}
                  </button>
                )}
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p>Sin lecturas recibidas para esta selección.</p>
      )}
    </Card>
  );
}
