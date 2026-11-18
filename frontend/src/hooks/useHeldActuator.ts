import { useCallback, useEffect, useRef, useState } from "react";
import type { ButtonHTMLAttributes } from "react";
import { createSessionId } from "../services/session";

export interface ActuatorLease {
  epoch: number;
  window_id: string;
  ticket?: string;
}

/** Browser intentions only. No physical output or confirmation is provided. */
export function useHeldActuator<A extends string>(options: {
  demo: boolean;
  physical?: boolean;
  enabled: boolean;
  blocked?: boolean;
  lease: ActuatorLease | null;
  send: (
    action: A | "stop",
    session: string,
    seq: number,
    lease: ActuatorLease,
    all: boolean,
  ) => Promise<ActuatorLease>;
}) {
  const config = useRef(options);
  config.current = options;
  const lease = useRef<ActuatorLease | null>(null);
  if (
    options.lease &&
    (!lease.current || options.lease.epoch >= lease.current.epoch)
  )
    lease.current = {
      epoch: options.lease.epoch,
      window_id: options.lease.window_id,
      ticket: options.lease.ticket,
    };
  const session = useRef(createSessionId()),
    sequence = useRef(0),
    generation = useRef(0);
  const held = useRef<{ action: A; input: number | "keyboard" } | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const busy = useRef(false),
    stopping = useRef(false);
  const [action, setAction] = useState<A | "stop">("stop");
  const [pendingStop, setPendingStop] = useState(false);
  const [technicalError, setTechnicalError] = useState<string | null>(null);
  const [message, setMessage] = useState(
    options.demo
      ? "Mantén pulsado para mover. Suelta para detener."
      : "Mantén pulsado solo mientras observas el robot.",
  );
  const cancel = useCallback(() => {
    generation.current++;
    held.current = null;
    stopping.current = false;
    setPendingStop(false);
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    setAction("stop");
  }, []);
  const updateLease = (value: ActuatorLease) => {
    if (!lease.current || value.epoch >= lease.current.epoch)
      lease.current = {
        epoch: value.epoch,
        window_id: value.window_id,
        ticket: value.ticket,
      };
  };
  const stop = useCallback(
    async (all = false) => {
      cancel();
      if (!config.current.demo && !config.current.physical) return;
      const current = generation.current;
      stopping.current = true;
      setPendingStop(true);
      try {
        const result = await config.current.send(
          "stop",
          session.current,
          ++sequence.current,
          lease.current || { epoch: 0, window_id: "" },
          all,
        );
        updateLease(result);
        if (generation.current === current) {
          setTechnicalError(null);
          setMessage(
            config.current.physical
              ? "Parada solicitada al robot."
              : "Parada confirmada por el simulador. Sin actuación física.",
          );
        }
      } catch (error) {
        if (generation.current === current) {
          setTechnicalError(String(error));
          setMessage(
            "Parada sin confirmación. Comprueba la conexión. El mando caduca.",
          );
        }
      } finally {
        if (generation.current === current) {
          stopping.current = false;
          setPendingStop(false);
        }
      }
    },
    [cancel],
  );
  const release = useCallback(
    (input?: number | "keyboard") => {
      if (held.current && (input === undefined || held.current.input === input))
        void stop();
    },
    [stop],
  );
  const start = useCallback(
    (next: A, input: number | "keyboard" = "keyboard") => {
      const c = config.current;
      if (c.physical && held.current && held.current.action !== next) {
        void stop();
        return false;
      }
      if (
        (!c.demo && !c.physical) ||
        !c.enabled ||
        c.blocked ||
        held.current ||
        stopping.current ||
        !lease.current
      )
        return false;
      const current = ++generation.current;
      const startingWindow = lease.current.window_id;
      held.current = { action: next, input };
      setAction(next);
      const send = async () => {
        if (
          !held.current ||
          busy.current ||
          generation.current !== current ||
          !lease.current
        )
          return;
        if (c.physical && startingWindow !== lease.current.window_id) {
          void stop();
          return;
        }
        busy.current = true;
        try {
          const result = await config.current.send(
            next,
            session.current,
            ++sequence.current,
            lease.current,
            false,
          );
          if (held.current && generation.current === current) {
            updateLease(result);
            setTechnicalError(null);
            setMessage(
              c.physical
                ? "Orden recibida por el sistema."
                : "Solicitud aceptada por el simulador. Sin actuación física.",
            );
          }
        } catch (error) {
          if (generation.current === current) {
            void stop();
            setTechnicalError(String(error));
            setMessage(
              "Movimiento no disponible. Comprueba la conexión antes de volver a pulsar.",
            );
          }
        } finally {
          busy.current = false;
        }
      };
      void send();
      timer.current = setInterval(() => void send(), 150);
      return true;
    },
    [stop],
  );
  useEffect(() => {
    if ((!options.enabled || options.blocked) && held.current) void stop();
  }, [options.enabled, options.blocked, stop]);
  useEffect(() => {
    const away = () => release();
    const pointer = (event: PointerEvent) => release(event.pointerId);
    const hidden = () => {
      if (document.hidden) away();
    };
    window.addEventListener("blur", away);
    window.addEventListener("offline", away);
    window.addEventListener("pagehide", away);
    window.addEventListener("pointerup", pointer);
    window.addEventListener("pointercancel", pointer);
    document.addEventListener("visibilitychange", hidden);
    return () => {
      away();
      if (timer.current) clearInterval(timer.current);
      window.removeEventListener("blur", away);
      window.removeEventListener("offline", away);
      window.removeEventListener("pagehide", away);
      window.removeEventListener("pointerup", pointer);
      window.removeEventListener("pointercancel", pointer);
      document.removeEventListener("visibilitychange", hidden);
    };
  }, [release]);
  const bind = (next: A): ButtonHTMLAttributes<HTMLButtonElement> => ({
    onPointerDown: (e) => {
      if (e.button !== 0) return;
      e.preventDefault();
      if (start(next, e.pointerId))
        e.currentTarget.setPointerCapture(e.pointerId);
    },
    onPointerUp: (e) => release(e.pointerId),
    onPointerCancel: (e) => release(e.pointerId),
    onLostPointerCapture: (e) => release(e.pointerId),
    onBlur: () => release(),
    onKeyDown: (e) => {
      if ([" ", "Enter"].includes(e.key)) {
        e.preventDefault();
        if (!e.repeat) start(next);
      }
    },
    onKeyUp: (e) => {
      if ([" ", "Enter"].includes(e.key)) {
        e.preventDefault();
        release("keyboard");
      }
    },
  });
  return {
    action,
    message,
    pendingStop,
    technicalError,
    start,
    stop,
    release,
    cancel,
    bind,
  };
}
