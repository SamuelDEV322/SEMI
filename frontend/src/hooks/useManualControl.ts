import { useState } from "react";
import { api } from "../services/api";
import { useRuntime } from "../Runtime";
import { useHeldActuator } from "./useHeldActuator";
import type { Action, RobotStatus, Speed } from "../types/api";

export function useManualControl(robot: RobotStatus | null, online: boolean) {
  const runtime = useRuntime();
  const [speed, setSpeed] = useState<Speed>("low");
  const control = useHeldActuator<Exclude<Action, "stop">>({
    demo: runtime.mode === "demonstration",
    enabled: online,
    blocked: robot?.surface_trial?.blocked,
    lease: robot?.control || null,
    send: async (action, session_id, seq, lease, all) => {
      const ack = await api.command({
        mode: "demonstration",
        domain: all ? "all" : "traction",
        action,
        speed,
        session_id,
        seq,
        ...lease,
      });
      return ack.control;
    },
  });
  return { ...control, speed, setSpeed, stopAll: () => control.stop(true) };
}
