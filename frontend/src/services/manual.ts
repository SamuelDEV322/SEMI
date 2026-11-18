import { post } from "./api";
import type { ActuatorLease } from "../hooks/useHeldActuator";
export type Mechanism = "traction" | "rack";
export interface ManualChannel extends ActuatorLease {
  ticket: string;
  ready: boolean;
  armed: boolean;
  action: string;
}
export type ManualState = Record<Mechanism, ManualChannel>;
export function mechanism(channel?: ManualChannel) {
  if (!channel?.ready) return "No disponible";
  if (!channel.armed) return "Pendiente de habilitar";
  return channel.action === "stop"
    ? "Disponible"
    : "Orden de movimiento activa";
}
export async function manual(
  key: string,
  domain: Mechanism | "all",
  action: string,
  lease?: ActuatorLease,
  session_id?: string,
  seq?: number,
  speed = "low",
) {
  if (!window.isSecureContext)
    throw new Error(
      "Abre el mando en localhost o mediante HTTPS para usar la clave.",
    );
  return post<ManualState>(
    "control/manual/",
    {
      domain,
      action,
      epoch: lease?.epoch,
      window_id: lease?.window_id,
      ticket: lease?.ticket,
      session_id,
      seq,
      speed,
    },
    "POST",
    { "X-SEMI-Operator": key },
  );
}
