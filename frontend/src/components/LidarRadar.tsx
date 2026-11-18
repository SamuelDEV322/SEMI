import { lidarMessage } from "../services/sourceStatus";
import { useScanFreshness } from "../hooks/useScanFreshness";
import { Radar } from "lucide-react";
import type { Scan } from "../types/api";
import { Empty } from "./ui";
export function LidarRadar({ scan }: { scan: Scan | null }) {
  const expired = useScanFreshness(scan);
  const valid = scan?.valid && !expired && scan.points.length > 0;
  return (
    <div
      className={`radar-panel ${scan?.source === "mock" ? "radar-simulated" : ""}`}
    >
      <div className="radar-heading">
        <span>
          <Radar size={15} /> Distancias alrededor de SEMI
        </span>
        <small>
          {!scan
            ? "LiDAR · Sin datos"
            : scan.source === "mock"
              ? "LiDAR · Simulación"
              : scan?.source === "replay"
                ? "REPRODUCCIÓN"
                : valid
                  ? "LiDAR conectado · escaneando"
                  : "LiDAR sin lecturas"}
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
          <g className="radar-distances">
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
          </g>
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
        <Empty>{lidarMessage(scan, expired)}</Empty>
      )}
      <div className="radar-footer">
        {valid ? `${scan.points.length} distancias` : "Sin escaneo activo"} ·{" "}
        {!scan
          ? "Sin datos"
          : scan.source === "real"
            ? valid
              ? "Distancias medidas en tiempo real"
              : "Entrada USB"
            : "Datos de prueba"}
      </div>
    </div>
  );
}
