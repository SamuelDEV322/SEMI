import { useState, useEffect, useRef } from "react";
import type { SetupPlot, SetupAction, Sector } from "../types/setup";
export function SectorManager({
  plot,
  act,
  busy,
}: {
  plot: SetupPlot;
  act: SetupAction;
  busy: boolean;
}) {
  const [name, setName] = useState(""),
    [edit, setEdit] = useState<number>(),
    [pending, setPending] = useState<{ sector: Sector; action: string } | null>(
      null,
    ),
    [failed, setFailed] = useState(false);
  const nameInput = useRef<HTMLInputElement>(null);
  const active = plot.zones.filter((z) => !z.archived),
    archived = plot.zones.filter((z) => z.archived);
  const row = (z: Sector) => (
    <li className="sector-card" key={z.id}>
      <strong>{z.name}</strong>
      <span>
        {z.point_count} lugares asociados{z.archived ? " · Archivado" : ""}
        {z.historical_surface ? " · Registro histórico de ensayo" : ""}
      </span>
      {!z.archived && (
        <div className="action-row">
          <button
            type="button"
            className="button"
            onClick={() => {
              setEdit(z.id);
              setName(z.name);
              nameInput.current?.focus();
            }}
          >
            Renombrar {z.name}
          </button>
          <button
            type="button"
            className="button"
            onClick={() => {
              setFailed(false);
              setPending({
                sector: z,
                action:
                  z.point_count || z.has_history
                    ? "sector_archive"
                    : "sector_delete",
              });
            }}
          >
            {z.point_count || z.has_history ? "Archivar" : "Eliminar"} {z.name}
          </button>
          {z.point_count > 0 && (
            <button
              type="button"
              className="button"
              onClick={() => {
                setFailed(false);
                setPending({ sector: z, action: "sector_detach" });
              }}
            >
              Desvincular lugares de {z.name}
            </button>
          )}
        </div>
      )}
      {z.archived && !z.historical_surface && (
        <button
          type="button"
          className="button"
          disabled={busy}
          onClick={() => act("sector_restore", { zone: z.id })}
        >
          Recuperar {z.name}
        </button>
      )}
    </li>
  );
  return (
    <div className="sector-manager">
      <p>
        Los sectores son nombres para organizar tu cafetal. Son opcionales y no
        indican materiales ni límites en un mapa.
      </p>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          if (await act("sector", { zone: edit, name })) {
            setName("");
            setEdit(undefined);
          }
        }}
      >
        <label>
          Nombre del sector
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            maxLength={80}
            required
            placeholder="Ejemplo: Zona alta"
          />
        </label>
        <div className="action-row">
          <button className="button primary" disabled={busy || !name.trim()}>
            {edit ? "Guardar nombre del sector" : "Agregar sector"}
          </button>
          {edit && (
            <button
              type="button"
              className="button"
              onClick={() => {
                setEdit(undefined);
                setName("");
              }}
            >
              Cancelar cambio
            </button>
          )}
        </div>
      </form>
      <ul className="sector-list">{active.map(row)}</ul>
      {!active.length && (
        <p>Aún no tienes sectores. Puedes continuar sin crearlos.</p>
      )}
      {archived.length > 0 && (
        <details>
          <summary>Consultar sectores archivados ({archived.length})</summary>
          <p>
            Sus lugares y mediciones se conservan. Los registros antiguos de
            ensayo no se ofrecen al crear nuevos lugares.
          </p>
          <ul className="sector-list">{archived.map(row)}</ul>
        </details>
      )}
      {pending && (
        <ConfirmDialog
          title={`${pending.action === "sector_delete" ? "Eliminar" : pending.action === "sector_archive" ? "Archivar" : "Desvincular lugares de"} ${pending.sector.name}`}
          busy={busy}
          onCancel={() => setPending(null)}
          onConfirm={async () => {
            if (
              await act(pending.action, {
                zone: pending.sector.id,
                confirmed: true,
              })
            )
              setPending(null);
            else setFailed(true);
          }}
        >
          <p>
            {pending.action === "sector_delete"
              ? "Se eliminará este sector vacío. No se eliminará ninguna medición."
              : pending.action === "sector_archive"
                ? "El sector dejará de aparecer entre las opciones activas. Sus lugares y mediciones permanecerán disponibles."
                : "Los lugares seguirán en el cafetal sin sector. Sus mediciones y la asociación anterior se conservarán."}
          </p>
          {failed && (
            <p role="alert">
              No se pudo guardar el cambio. Comprueba la conexión e inténtalo de
              nuevo.
            </p>
          )}
        </ConfirmDialog>
      )}
    </div>
  );
}
function ConfirmDialog({
  title,
  children,
  busy,
  onCancel,
  onConfirm,
}: {
  title: string;
  children: React.ReactNode;
  busy: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current!;
    d.showModal();
    return () => d.close();
  }, []);
  return (
    <dialog
      ref={ref}
      className="confirm-dialog"
      aria-label={title}
      onCancel={(e) => {
        e.preventDefault();
        onCancel();
      }}
    >
      <h2>{title}</h2>
      {children}
      <div className="action-row">
        <button className="button" autoFocus onClick={onCancel}>
          Cancelar
        </button>
        <button className="button primary" disabled={busy} onClick={onConfirm}>
          Confirmar
        </button>
      </div>
    </dialog>
  );
}
