import { useState, useEffect, useCallback } from "react";
import { usePolling } from "../hooks/usePolling";
import { api } from "../services/api";
import type { Sample, SamplingPoint } from "../types/api";
import type { SetupPlot, SetupAction } from "../types/setup";
import { Card, Reading, Empty, dateTime, ErrorNotice } from "../components/ui";
import { TimeChart, SamplingPlot, metricLabels } from "../components/Charts";
import type { Metric } from "../components/Charts";
import { SectorManager } from "../components/SectorManager";
import { PointEditor } from "../components/PointEditor";
import { useRuntime } from "../Runtime";
const failed =
  "No pudimos cargar tus datos. Comprueba la conexión e inténtalo de nuevo";
export function Data({
  plot,
  act,
  setupBusy,
  onConfigure,
  samples,
  points,
  pointsLoading,
  onRefresh,
  historyError,
  pointsError,
}: {
  plot: SetupPlot | null;
  act: SetupAction;
  setupBusy: boolean;
  onConfigure: () => void;
  samples: Sample[];
  points: SamplingPoint[];
  pointsLoading: boolean;
  onRefresh: () => void;
  historyError: string | null;
  pointsError: string | null;
}) {
  const runtime = useRuntime();
  const demo = runtime.mode === "demonstration";
  const [sector, setSector] = useState(""),
    [archived, setArchived] = useState(false),
    [selected, setSelected] = useState<number>(),
    [metric, setMetric] = useState<Metric>("soil_moisture"),
    [range, setRange] = useState("all"),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [technical, setTechnical] = useState(""),
    [notice, setNotice] = useState("");
  useEffect(() => {
    if (
      sector &&
      !plot?.zones.some(
        (z) => String(z.id) === sector && (!z.archived || archived),
      )
    ) {
      setSector("");
      setSelected(undefined);
    }
  }, [plot?.zones, sector, archived]);
  const filtered = points.filter(
      (p) =>
        !sector ||
        p.zone === Number(sector) ||
        (archived &&
          plot?.zones.find((z) => z.id === Number(sector))?.archived &&
          p.sector_history?.some((z) => z.id === Number(sector))),
    ),
    point = filtered.find((p) => p.id === selected) || filtered[0];
  const loadHistory = useCallback(
    () => api.pointHistory(point?.id, range),
    [point?.id, range],
  );
  const history = usePolling(loadHistory, 5000);
  const rows = (history.data || []).filter(
    (s) => s.sampling_point === point?.id,
  );
  const latest = point?.latest_sample;
  useEffect(() => {
    setNotice("");
  }, [point?.id]);
  const mutate: SetupAction = async (a, d) => {
    const p = await act(a, d);
    if (p) {
      onRefresh();
      history.refresh();
    }
    return p;
  };
  const capture = async () => {
    if (!point || !runtime.npk_capture) return;
    setBusy(true);
    setError("");
    try {
      await api.capture(point.name, point.id);
      setNotice(
        demo
          ? "Medición simulada guardada en este lugar."
          : "Medición guardada en este lugar.",
      );
      onRefresh();
      history.refresh();
    } catch (e) {
      setTechnical(String(e));
      setError(
        "No pudimos guardar la medición. Comprueba la conexión y que SEMI esté detenido.",
      );
    } finally {
      setBusy(false);
    }
  };
  if (!plot)
    return (
      <Card title="Mi cafetal">
        <p>
          Guarda primero el nombre de tu cafetal para organizar tus mediciones.
        </p>
        <button className="button primary" onClick={onConfigure}>
          Preparar mi cafetal
        </button>
      </Card>
    );
  return (
    <div className="page-stack data-hub">
      <Card title="Mi cafetal">
        <h3>{plot.name}</h3>
        <p>Elige dónde mediste para consultar sus resultados.</p>
        <label>
          Sector para consultar (opcional)
          <select
            value={sector}
            onChange={(e) => {
              setSector(e.target.value);
              setSelected(undefined);
            }}
          >
            <option value="">Todos los lugares</option>
            {plot.zones
              .filter((z) => !z.archived)
              .map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
            {archived && (
              <optgroup label="Sectores archivados">
                {plot.zones
                  .filter((z) => z.archived)
                  .map((z) => (
                    <option key={z.id} value={z.id}>
                      {z.name} (archivado)
                    </option>
                  ))}
              </optgroup>
            )}
          </select>
        </label>
        {plot.zones.some((z) => z.archived) && (
          <label className="check-row">
            <input
              type="checkbox"
              checked={archived}
              onChange={(e) => {
                setArchived(e.target.checked);
                setSector("");
              }}
            />
            Consultar también sectores archivados
          </label>
        )}
        <details>
          <summary>Administrar sectores</summary>
          <SectorManager plot={plot} busy={setupBusy} act={mutate} />
        </details>
      </Card>
      <Card title="Lugares para medir">
        <ErrorNotice message={pointsError ? failed : null} />
        {pointsLoading ? (
          <p role="status">Cargando tus lugares…</p>
        ) : (
          !pointsError && (
            <>
              {filtered.length ? (
                <label>
                  ¿Dónde mediste?
                  <select
                    aria-label="Lugar para consultar"
                    value={point?.id || ""}
                    onChange={(e) => setSelected(Number(e.target.value))}
                  >
                    {filtered.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.display_name || p.name}
                      </option>
                    ))}
                  </select>
                </label>
              ) : (
                <Empty>
                  {sector
                    ? "Este sector todavía no tiene lugares."
                    : "Todavía no tienes lugares para medir."}
                </Empty>
              )}
              {point && (
                <p>
                  {point.x === null
                    ? "Lugar guardado sin ubicación. Puedes ubicarlo más adelante."
                    : "Ubicación relativa elegida manualmente."}
                </p>
              )}
            </>
          )
        )}
        <details>
          <summary>Agregar o modificar lugares</summary>
          <PointEditor
            plot={plot}
            busy={setupBusy}
            act={mutate}
            onSaved={(id) => {
              setSector("");
              setSelected(id);
            }}
          />
        </details>
      </Card>
      {point && !pointsError && (
        <>
          <Card title="Resultados">
            <h3>{point.display_name || point.name}</h3>
            {latest ? (
              <>
                <p>Medición del {dateTime(latest.captured_at)}</p>
                <p>
                  {latest.source === "real"
                    ? "Lectura de sensor"
                    : latest.source === "replay"
                      ? "Registro de prueba"
                      : "Datos simulados"}{" "}
                  ·{" "}
                  {latest.status === "valid"
                    ? "Lectura válida"
                    : "Lectura no válida"}{" "}
                  ·{" "}
                  {latest.freshness === "stale" ? "Desactualizada" : "Reciente"}
                </p>
                <div className="reading-grid two">
                  {(
                    [
                      "soil_moisture",
                      "nitrogen",
                      "phosphorus",
                      "potassium",
                    ] as Metric[]
                  ).map((m) => (
                    <Reading
                      key={m}
                      label={metricLabels[m]}
                      value={latest.status === "valid" ? latest[m] : null}
                      unit={m === "soil_moisture" ? "%" : latest.npk_unit}
                      stale={latest.freshness === "stale"}
                      note={
                        latest.source === "real"
                          ? "Lectura de sensor"
                          : "Datos simulados"
                      }
                    />
                  ))}
                </div>
                <p className="caption">
                  Estos valores no indican por sí solos si tu café necesita
                  fertilización.
                </p>
              </>
            ) : (
              <Empty>Todavía no tienes mediciones en este lugar</Empty>
            )}
            <button
              className="button primary wide"
              disabled={busy || !runtime.npk_capture}
              onClick={() => void capture()}
            >
              {demo ? "Guardar medición simulada" : "Tomar medición"}
            </button>
            <p>
              {demo
                ? "Solo demostración. No se utiliza una sonda física."
                : "Sensor de suelo no conectado. No se ha tomado ninguna medición."}
            </p>
            <p role="status">{notice}</p>
            <ErrorNotice message={error} />
          </Card>
          <Card title="Historial de este lugar">
            <p>{point.display_name || point.name}</p>
            <div className="filter-grid">
              <label>
                Variable
                <select
                  value={metric}
                  onChange={(e) => setMetric(e.target.value as Metric)}
                >
                  {Object.entries(metricLabels).map(([k, v]) => (
                    <option key={k} value={k}>
                      {v}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Periodo
                <select
                  value={range}
                  onChange={(e) => setRange(e.target.value)}
                >
                  <option value="all">Todo el historial</option>
                  <option value="24">Últimas 24 horas</option>
                  <option value="168">Últimos 7 días</option>
                </select>
              </label>
            </div>
            {history.error || historyError ? (
              <>
                <ErrorNotice message={failed} />
                <button
                  className="button"
                  onClick={() => {
                    history.refresh();
                    onRefresh();
                  }}
                >
                  Intentar de nuevo
                </button>
              </>
            ) : history.loading ? (
              <p role="status">Cargando tus mediciones…</p>
            ) : rows.length ? (
              <>
                <TimeChart samples={rows} metric={metric} />
                <h3>Registro de mediciones</h3>
                <div className="sample-list">
                  {rows.map((s) => (
                    <article className="sample-row" key={s.id}>
                      <div>
                        <strong>{dateTime(s.captured_at)}</strong>
                        <span className="sample-tag">
                          {s.source === "real"
                            ? "Lectura de sensor"
                            : "Datos simulados"}{" "}
                          · {s.status === "valid" ? "válida" : "inválida"} ·{" "}
                          {s.freshness === "stale"
                            ? "desactualizada"
                            : "reciente"}
                        </span>
                      </div>
                      <div className="sample-values">
                        <span>
                          N {s.nitrogen ?? "—"} · P {s.phosphorus ?? "—"} · K{" "}
                          {s.potassium ?? "—"} {s.npk_unit}
                        </span>
                        <span>
                          Humedad {s.soil_moisture ?? "—"} {s.moisture_unit}
                        </span>
                      </div>
                    </article>
                  ))}
                </div>
              </>
            ) : (
              <Empty>
                {range === "all"
                  ? "Todavía no tienes mediciones en este lugar"
                  : "No hay mediciones en el periodo elegido."}
              </Empty>
            )}
            {!!point.sector_history?.length && (
              <details>
                <summary>Asociaciones conservadas del lugar</summary>
                <ul>
                  {point.sector_history.map((z) => (
                    <li key={z.id}>
                      {z.name}
                      {z.archived ? " · Archivado" : ""}
                    </li>
                  ))}
                </ul>
                <p>
                  Esta lista conserva sectores vinculados al lugar; no atribuye
                  una ubicación física a cada lectura antigua.
                </p>
              </details>
            )}
          </Card>
        </>
      )}
      <Card title="Esquema de mis lugares">
        {pointsError ? (
          <ErrorNotice message={failed} />
        ) : pointsLoading ? (
          <p>Cargando…</p>
        ) : (
          <SamplingPlot points={filtered} zones={plot.zones} />
        )}
      </Card>
      {samples.some((s) => !s.sampling_point) && (
        <details>
          <summary>Mediciones anteriores sin lugar asociado</summary>
          {samples
            .filter((s) => !s.sampling_point)
            .map((s) => (
              <p key={s.id}>
                {s.point_label} · {dateTime(s.captured_at)} · Registro
                conservado
              </p>
            ))}
        </details>
      )}
      {runtime.dev_tools && (
        <details className="diagnostics">
          <summary>Diagnóstico técnico de mediciones</summary>
          <pre>
            {JSON.stringify(
              {
                pointsError,
                historyError,
                pointHistoryError: history.error,
                technical,
                ambientSensors: "not_confirmed",
              },
              null,
              2,
            )}
          </pre>
        </details>
      )}
    </div>
  );
}
