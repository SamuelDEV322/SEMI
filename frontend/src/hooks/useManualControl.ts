import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { createSessionId } from "../services/session";
import type { Action, ControlState, RobotStatus, Speed } from "../types/api";

export function useManualControl(robot: RobotStatus | null, online: boolean) {
  const [action, setAction] = useState<Action>("stop"),
    [speed, setSpeed] = useState<Speed>("low"),
    [message, setMessage] = useState(
      "Control de demostración. Mantén un botón para mover.",
    ),
    [pendingStop, setPendingStop] = useState(false),
    [technicalError, setTechnicalError] = useState<string | null>(null);
  const session = useRef(createSessionId()),
    seq = useRef(0),
    control = useRef<ControlState | null>(null),
    held = useRef(false),
    busy = useRef(false),
    timer = useRef<ReturnType<typeof setInterval> | null>(null),
    speedRef = useRef(speed),
    active = useRef<Action>("stop");
  speedRef.current = speed;
  if (
    robot &&
    (!control.current || robot.control.epoch >= control.current.epoch)
  )
    control.current = robot.control;
  const stop = useCallback(async () => {
    held.current = false;
    active.current = "stop";
    setAction("stop");
    if (timer.current) clearInterval(timer.current);
    timer.current = null;
    setPendingStop(true);
    const c = control.current;
    try {
      const ack = await api.command({
        mode: "demonstration",
        action: "stop",
        speed: speedRef.current,
        session_id: session.current,
        seq: ++seq.current,
        epoch: c?.epoch || 0,
        window_id: c?.window_id || "",
      });
      if (!control.current || ack.control.epoch >= control.current.epoch)
        control.current = ack.control;
      setMessage("Parada confirmada por el simulador. Sin actuación física.");
    } catch (error) {
      setTechnicalError(String(error));
      setMessage(
        "Parada sin confirmación. Comprueba la conexión. El mando simulado caduca.",
      );
    } finally {
      setPendingStop(false);
    }
  }, []);
  const start = useCallback(
    (next: Action) => {
      if (held.current || pendingStop || !online || !control.current) return;
      held.current = true;
      active.current = next;
      setAction(next);
      const send = async () => {
        if (!held.current || busy.current) return;
        const c = control.current;
        if (!c) return;
        busy.current = true;
        try {
          const ack = await api.command({
            mode: "demonstration",
            action: active.current,
            speed: speedRef.current,
            session_id: session.current,
            seq: ++seq.current,
            epoch: c.epoch,
            window_id: c.window_id,
          });
          if (held.current) {
            if (!control.current || ack.control.epoch >= control.current.epoch)
              control.current = ack.control;
            setMessage("Movimiento confirmado en el simulador.");
          }
        } catch (error) {
          setTechnicalError(String(error));
          setMessage(
            "Movimiento no disponible. Comprueba la conexión antes de volver a pulsar.",
          );
          void stop();
        } finally {
          busy.current = false;
        }
      };
      void send();
      timer.current = setInterval(() => void send(), 150);
    },
    [online, pendingStop, stop],
  );
  useEffect(() => {
    if ((!online || robot?.surface_trial?.blocked) && held.current) void stop();
  }, [online, robot?.surface_trial?.blocked, stop]);
  useEffect(() => {
    const release = () => {
      if (held.current) void stop();
    };
    const hidden = () => {
      if (document.hidden) release();
    };
    window.addEventListener("blur", release);
    window.addEventListener("pagehide", release);
    window.addEventListener("pointerup", release);
    window.addEventListener("pointercancel", release);
    document.addEventListener("visibilitychange", hidden);
    return () => {
      release();
      if (timer.current) clearInterval(timer.current);
      window.removeEventListener("blur", release);
      window.removeEventListener("pagehide", release);
      window.removeEventListener("pointerup", release);
      window.removeEventListener("pointercancel", release);
      document.removeEventListener("visibilitychange", hidden);
    };
  }, [stop]);
  const release = () => {
    if (held.current) void stop();
  };
  return {
    action,
    speed,
    setSpeed,
    message,
    pendingStop,
    technicalError,
    start,
    stop,
    release,
  };
}
