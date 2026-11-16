import type { Sample, SamplingPoint } from "../types/api";
import { RelativeMap } from "./RelativeMap";
import { Empty, dateTime } from "./ui";
export type Metric = "soil_moisture" | "nitrogen" | "phosphorus" | "potassium";
export const metricLabels: Record<Metric, string> = {
  soil_moisture: "Humedad del suelo",
  nitrogen: "Nitrógeno",
  phosphorus: "Fósforo",
  potassium: "Potasio",
};
export function TimeChart({
  samples,
  metric,
}: {
  samples: Sample[];
  metric: Metric;
}) {
  const pointIds = new Set(samples.map((s) => s.sampling_point));
  if (pointIds.size > 1)
    return <Empty>Selecciona un único punto para esta gráfica.</Empty>;
  const rows = [...samples].sort(
    (a, b) => Date.parse(a.captured_at) - Date.parse(b.captured_at),
  );
  const valid = rows.filter(
    (row) => row.status === "valid" && row[metric] !== null,
  );
  if (!valid.length) return <Empty>Sin lecturas para esta variable</Empty>;
  const times = rows.map((r) => new Date(r.captured_at).getTime()),
    min = Math.min(...times),
    span = Math.max(...times) - min || 1,
    max = Math.max(...valid.map((r) => r[metric]!)) * 1.2 || 1;
  const x = (r: Sample) =>
      40 + ((new Date(r.captured_at).getTime() - min) / span) * 480,
    y = (r: Sample) => 155 - (r[metric]! / max) * 120;
  const segments: string[] = [];
  let current: string[] = [];
  rows.forEach((r) => {
    if (r.status === "invalid" || r[metric] === null) {
      if (current.length) segments.push(current.join(" "));
      current = [];
    } else current.push(`${x(r)},${y(r)}`);
  });
  if (current.length) segments.push(current.join(" "));
  return (
    <div className="chart">
      <svg
        viewBox="0 0 550 190"
        role="img"
        aria-label={`Gr\u00e1fica temporal de ${metricLabels[metric]}, datos de demostraci\u00f3n`}
      >
        {[0, 0.5, 1].map((f) => (
          <g key={f}>
            <line
              x1="40"
              x2="525"
              y1={155 - f * 120}
              y2={155 - f * 120}
              stroke="var(--border)"
            />
            <text
              x="32"
              y={159 - f * 120}
              textAnchor="end"
              fontSize="16"
              fill="var(--muted)"
            >
              {Math.round(max * f)}
            </text>
          </g>
        ))}
        {segments.map((points, i) => (
          <polyline
            key={i}
            points={points}
            fill="none"
            stroke="var(--accent)"
            strokeWidth="2"
          />
        ))}
        {valid.map((r) => (
          <circle key={r.id} cx={x(r)} cy={y(r)} r="3" fill="var(--accent)">
            <title>{`${r.point_label}: ${r[metric]} ${metric === "soil_moisture" ? "%" : r.npk_unit}`}</title>
          </circle>
        ))}
        <text x="40" y="180" fontSize="16" fill="var(--muted)">
          {new Date(min).toLocaleTimeString("es-CO", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </text>
        <text
          x="525"
          y="180"
          textAnchor="end"
          fontSize="16"
          fill="var(--muted)"
        >
          {new Date(Math.max(...times)).toLocaleTimeString("es-CO", {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </text>
      </svg>
      <p className="caption">
        {metric === "soil_moisture" ? "%" : "mg/kg"} - datos de prueba - los
        huecos no se interpolan
      </p>
    </div>
  );
}
export function SamplingPlot({
  points,
  zones = [],
}: {
  points: SamplingPoint[];
  zones?: { id: number; name: string; archived?: boolean }[];
}) {
  if (!points.length)
    return <Empty>Todavía no tienes lugares para medir.</Empty>;
  const located = points.filter((p) => p.x !== null && p.y !== null);
  return (
    <>
      {located.length ? (
        <RelativeMap points={located} />
      ) : (
        <p>
          No hay ubicaciones marcadas. Tus lugares y mediciones siguen
          disponibles.
        </p>
      )}
      <ul className="point-map-readings">
        {points.map((p) => (
          <li key={p.id}>
            <strong>{p.display_name || p.name}</strong>
            <span>
              {zones.find((z) => z.id === p.zone)?.name || "Sin sector"}
              {zones.find((z) => z.id === p.zone)?.archived
                ? " · Archivado"
                : ""}
            </span>
            <span>
              {p.latest_sample
                ? `Última medición: ${dateTime(p.latest_sample.captured_at)}`
                : "Todavía no tienes mediciones en este lugar"}
            </span>
            {p.latest_sample && (
              <span>
                {p.latest_sample.source === "real"
                  ? "Sensor"
                  : "Datos simulados"}{" "}
                · {p.latest_sample.status === "valid" ? "válida" : "inválida"} ·{" "}
                {p.latest_sample.freshness === "stale"
                  ? "desactualizada"
                  : "reciente"}
              </span>
            )}
          </li>
        ))}
      </ul>
    </>
  );
}
