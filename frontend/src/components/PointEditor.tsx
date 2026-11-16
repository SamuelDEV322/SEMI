import { useState, useRef } from "react";
import type { SetupPlot, SetupAction } from "../types/setup";
import { RelativeMap } from "./RelativeMap";
export function PointEditor({
  plot,
  act,
  busy,
  onSaved,
}: {
  plot: SetupPlot;
  act: SetupAction;
  busy: boolean;
  onSaved?: (id: number) => void;
}) {
  const [edit, setEdit] = useState<number>(),
    [name, setName] = useState(""),
    [zone, setZone] = useState(""),
    [located, setLocated] = useState(false),
    [position, setPosition] = useState<{ x: number; y: number } | null>(null),
    [notice, setNotice] = useState("");
  const reset = () => {
    setEdit(undefined);
    setName("");
    setZone("");
    setLocated(false);
    setPosition(null);
  };
  const nameInput = useRef<HTMLInputElement>(null);
  const active = plot.zones.filter((z) => !z.archived),
    current = plot.points.find((p) => p.id === edit);
  return (
    <div className="point-editor">
      <p>
        Marca los lugares donde tomarás mediciones. Así podrás consultar sus
        resultados cada vez que vuelvas.
      </p>
      <p>No son destinos automáticos ni limitan por dónde conduces.</p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          const updated = await act("point", {
            point: edit,
            name,
            zone: zone ? Number(zone) : null,
            x: located ? (position?.x ?? null) : null,
            y: located ? (position?.y ?? null) : null,
          });
          if (updated) {
            const point = edit
              ? updated.points.find((p) => p.id === edit)
              : updated.points.find(
                  (p) => !plot.points.some((old) => old.id === p.id),
                );
            if (point) {
              setNotice(
                `${point.code} guardado. Ya puedes tomar una medición.`,
              );
              onSaved?.(point.id);
            }
            reset();
          }
        }}
      >
        <label>
          Nombre del lugar (opcional)
          <input
            ref={nameInput}
            value={name}
            maxLength={40}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ejemplo: Cerca de la entrada"
          />
        </label>
        {(active.length > 0 || current?.zone) && (
          <label>
            Sector (opcional)
            <select
              aria-label="Sector (opcional)"
              value={zone}
              onChange={(e) => setZone(e.target.value)}
            >
              <option value="">Sin sector</option>
              {active.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.name}
                </option>
              ))}
              {current?.zone &&
                plot.zones.find((z) => z.id === current.zone)?.archived && (
                  <option value={current.zone}>
                    {plot.zones.find((z) => z.id === current.zone)?.name}{" "}
                    (archivado)
                  </option>
                )}
            </select>
          </label>
        )}
        <label className="check-row">
          <input
            type="checkbox"
            checked={located}
            onChange={(e) => setLocated(e.target.checked)}
          />
          Marcar ubicación en el esquema (opcional)
        </label>
        {located && (
          <RelativeMap
            points={plot.points}
            position={position}
            onPick={setPosition}
          />
        )}
        {!located && (
          <p>Puedes guardar el lugar sin ubicación y marcarlo más adelante.</p>
        )}
        <div className="action-row">
          <button
            className="button primary"
            disabled={busy || (located && !position)}
          >
            {edit ? "Guardar cambios del lugar" : "Guardar lugar"}
          </button>
          {edit && (
            <button type="button" className="button" onClick={reset}>
              Crear otro lugar
            </button>
          )}
        </div>
      </form>
      <p role="status">{notice}</p>
      <ul className="sector-list">
        {plot.points.map((p) => (
          <li className="sector-card" key={p.id}>
            <strong>{p.name.split(" · T")[0]}</strong>
            <span>
              {p.x === null
                ? "Sin ubicación asignada"
                : "Ubicación relativa guardada"}{" "}
              · {p.latest_sample ? "Con mediciones" : "Todavía sin mediciones"}
            </span>
            <button
              type="button"
              className="button"
              onClick={() => {
                setEdit(p.id);
                setName(p.name.split(" · T")[0].replace(/^P\d+ /, ""));
                setZone(p.zone ? String(p.zone) : "");
                setLocated(p.x !== null);
                setPosition(
                  p.x !== null && p.y !== null ? { x: p.x, y: p.y } : null,
                );
              }}
            >
              Modificar {p.code || p.name}
            </button>
          </li>
        ))}
      </ul>
      {plot.demo && plot.points.length === 0 && (
        <>
          <button
            type="button"
            className="button"
            disabled={busy}
            onClick={async () => {
              if (
                await act("point", { name: "Ejemplo de entrada", x: 30, y: 50 })
              )
                await act("point", { name: "Ejemplo central", x: 70, y: 50 });
            }}
          >
            Crear puntos de ejemplo
          </button>
          <p>
            Solo demostración. Son ejemplos, no una recomendación de muestreo.
          </p>
        </>
      )}
    </div>
  );
}
