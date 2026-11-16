import { useState } from "react";
import { api } from "../services/api";
import { usePolling } from "../hooks/usePolling";
export function TrialTools() {
  const trial = usePolling(api.trial, 1500),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  const set = async (
    state: string,
    conservative = trial.data?.conservative ?? true,
  ) => {
    setBusy(true);
    setError("");
    try {
      await api.setTrial({ state, conservative });
      trial.refresh();
    } catch {
      setError(
        "No pudimos actualizar el ensayo. Comprueba la conexión e inténtalo de nuevo.",
      );
    } finally {
      setBusy(false);
    }
  };
  const labels: Record<string, string> = {
    inactive: "Ensayo desactivado",
    soil: "Condición normal simulada",
    sand: "Arena detectada (simulación)",
    unknown: "Superficie desconocida",
    lost: "Pérdida de detección",
  };
  const blocked =
    trial.data &&
    (trial.data.state === "sand" ||
      trial.data.state === "lost" ||
      (trial.data.state === "unknown" && trial.data.conservative));
  return (
    <section className="trial-panel" aria-label="Prueba de superficies">
      <h2>Prueba de superficies</h2>
      <p>
        Ensayo de laboratorio. No cambia los sectores del cafetal. Ningún sensor
        ha reconocido estos materiales.
      </p>
      {trial.error || error ? (
        <p role="alert">
          {error ||
            "No pudimos cargar el ensayo. Comprueba la conexión e inténtalo de nuevo."}
        </p>
      ) : (
        <p>
          Estado: {trial.data ? labels[trial.data.state] : "Cargando…"} · Origen
          simulado
        </p>
      )}
      <div className="action-row">
        {Object.entries(labels).map(([state, label]) => (
          <button
            className="button"
            key={state}
            disabled={busy}
            onClick={() => set(state)}
          >
            {label}
          </button>
        ))}
      </div>
      <label className="check-row">
        <input
          type="checkbox"
          checked={trial.data?.conservative ?? true}
          onChange={(e) =>
            set(trial.data?.state || "inactive", e.target.checked)
          }
        />
        Detener también ante incertidumbre (simulación)
      </label>
      {blocked && (
        <p className="notice danger" role="alert">
          STOP simulado. Movimiento cancelado en el simulador. Sin reversa ni
          giro automático.
        </p>
      )}
      <p>
        La condición normal no inicia movimiento. El control físico continúa
        bloqueado.
      </p>
    </section>
  );
}
