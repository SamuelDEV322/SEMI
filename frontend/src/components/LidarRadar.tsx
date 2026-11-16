import { useEffect, useRef, useState } from "react";
import { Radar } from "lucide-react";
import type { Scan } from "../types/api";
import { Empty } from "./ui";
export function LidarRadar({ scan }: { scan: Scan | null }) {
  const observed = useRef({ scan, at: performance.now() });
  const [, redraw] = useState(0);
  if (observed.current.scan !== scan)
    observed.current = { scan, at: performance.now() };
  useEffect(() => {
    const id = setInterval(() => redraw((n) => n + 1), 250);
    return () => clearInterval(id);
  }, []);
  const expired =
    scan?.source !== "mock" &&
    scan?.age_ms != null &&
    scan.age_ms + performance.now() - observed.current.at > 2000;
  const valid = scan?.valid && !expired && scan.points.length > 0;
  return (
    <div className="radar-panel">
      <div className="radar-heading">
        <span>
          <Radar size={15} /> Distancias alrededor de SEMI
        </span>
        <small>
          {!scan
            ? "SIN LECTURAS"
            : scan?.freshness === "stale"
              ? "Lectura desactualizada"
              : scan?.source === "real"
                ? "SENSOR USB · REAL"
                : scan?.source === "replay"
                  ? "REPRODUCCIÓN"
                  : "SIMULACIÓN"}
        </small>
      </div>
      {valid ? (
        <svg
          viewBox="0 0 300 245"
          role="img"
          aria-label={`Escaneo polar LiDAR. Fuente ${scan?.source === "real" ? "sensor" : scan?.source === "replay" ? "reproducción de prueba" : "simulación"}. Referencia local del robot, sin localización global.`}
        >
          <defs>
            <radialGradient id="radar-bg">
              <stop stopColor="var(--surface)" />
              <stop offset="1" stopColor="var(--bg)" />
            </radialGradient>
          </defs>
          <rect width="300" height="245" fill="url(#radar-bg)" />
          {[35, 70, 105].map((r) => (
            <circle
              key={r}
              cx="150"
              cy="120"
              r={r}
              fill="none"
              stroke="var(--border)"
              strokeDasharray="3 4"
            />
          ))}
          <path d="M150 12V228M42 120H258" stroke="var(--border)" />
          <text x="156" y="18" fontSize="12" fill="var(--muted)">
            {scan.source === "real" ? "0° SENSOR" : "FRENTE · 0°"}
          </text>
          <text x="240" y="115" fontSize="12" fill="var(--muted)">
            90°
          </text>
          {scan.points
            .filter(
              (p) =>
                p.valid &&
                p.distance !== null &&
                p.distance >= 0 &&
                p.distance <= scan.max_range_mm,
            )
            .map((p, i) => {
              const a = (p.angle_deg * Math.PI) / 180,
                r = (p.distance! / scan.max_range_mm) * 105;
              return (
                <circle
                  key={i}
                  cx={150 + Math.sin(a) * r}
                  cy={120 - Math.cos(a) * r}
                  r="2.1"
                  fill={
                    scan.freshness === "stale"
                      ? "var(--warning-text)"
                      : "var(--accent)"
                  }
                />
              );
            })}
          <rect
            x="142"
            y="112"
            width="16"
            height="21"
            rx="3"
            fill="var(--ink)"
          />
          <path d="m146 110 4-6 4 6" fill="var(--ink)" />
          <text
            x="150"
            y="242"
            textAnchor="middle"
            fontSize="12"
            fill="var(--muted)"
          >
            Alcance mostrado: {scan.max_range_mm / 1000} m · no es un mapa
          </text>
        </svg>
      ) : (
        <Empty>
          {expired || scan?.status === "stale"
            ? "Último escaneo desactualizado"
            : scan?.status === "error"
              ? "No se pudo obtener un escaneo"
              : scan?.status === "no_data"
                ? "Sensor sin lecturas"
                : "Sin escaneo disponible"}
        </Empty>
      )}
      <div className="radar-footer">
        {valid ? `${scan.points.length} distancias` : "Fuente no disponible"} ·{" "}
        {!scan
          ? "Sin datos"
          : scan.source === "real"
            ? "Solo lectura USB"
            : "Datos de prueba"}
      </div>
    </div>
  );
}
