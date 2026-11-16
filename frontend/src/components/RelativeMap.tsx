import { useId } from "react";
type Position = { x: number; y: number };
type Point = { id: number; code?: string; x: number | null; y: number | null };
export function RelativeMap({
  points,
  position,
  onPick,
}: {
  points: Point[];
  position?: Position | null;
  onPick?: (p: Position) => void;
}) {
  const hint = useId();
  const clamp = (n: number) => Math.max(0, Math.min(100, n));
  return (
    <>
      <div className="relative-map">
        <div
          className="relative-plane"
          role={onPick ? "button" : "img"}
          tabIndex={onPick ? 0 : undefined}
          aria-label={
            onPick
              ? "Elegir ubicación del lugar"
              : "Ubicaciones relativas elegidas por el usuario"
          }
          aria-describedby={hint}
          onClick={
            onPick
              ? (e) => {
                  const r = e.currentTarget.getBoundingClientRect();
                  onPick({
                    x: clamp(
                      Math.round(((e.clientX - r.left) / r.width) * 100),
                    ),
                    y: clamp(
                      Math.round(((e.clientY - r.top) / r.height) * 100),
                    ),
                  });
                }
              : undefined
          }
          onKeyDown={
            onPick
              ? (e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onPick(position || { x: 50, y: 50 });
                  } else if (e.key.startsWith("Arrow")) {
                    e.preventDefault();
                    const p = position || { x: 50, y: 50 };
                    onPick({
                      x: clamp(
                        p.x +
                          (e.key === "ArrowRight"
                            ? 2
                            : e.key === "ArrowLeft"
                              ? -2
                              : 0),
                      ),
                      y: clamp(
                        p.y +
                          (e.key === "ArrowDown"
                            ? 2
                            : e.key === "ArrowUp"
                              ? -2
                              : 0),
                      ),
                    });
                  }
                }
              : undefined
          }
        >
          {points
            .filter((p) => p.x !== null && p.y !== null)
            .map((p) => (
              <span
                key={p.id}
                className="relative-marker"
                style={{ left: `${p.x}%`, top: `${p.y}%` }}
              >
                {p.code || `P${p.id}`}
              </span>
            ))}
          {position && (
            <span
              className="relative-marker draft"
              style={{ left: `${position.x}%`, top: `${position.y}%` }}
            >
              ＋
            </span>
          )}
        </div>
      </div>
      <p className="caption" id={hint}>
        Esquema orientativo. No representa distancias reales.
        {onPick &&
          " Toca para marcar. Con teclado, Enter marca y las flechas ajustan."}
      </p>
    </>
  );
}
