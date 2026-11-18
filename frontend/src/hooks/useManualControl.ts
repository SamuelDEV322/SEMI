import { useState } from "react";
import { manual } from "../services/manual";
import { api } from "../services/api";
import { useRuntime } from "../Runtime";
import { useHeldActuator } from "./useHeldActuator";
import type { Action, RobotStatus, Speed } from "../types/api";

export function useManualControl(
  robot: RobotStatus | null,
  online: boolean,
  key: string,
) {
  const runtime = useRuntime();
  const [speed, setSpeed] = useState<Speed>("low");
  const control = useHeldActuator<Exclude<Action, "stop">>({
    demo: runtime.mode === "demonstration",
    enabled: online,
    physical: !!robot?.manual && !!key,
    blocked: robot?.surface_trial?.blocked,
    lease: robot?.manual?.traction || robot?.control || null,
    send: async (action, session_id, seq, lease, all) => {
      if (runtime.mode === "operational")
        return (
          await manual(
            key,
            all ? "all" : "traction",
            action,
            lease,
            session_id,
            seq,
            speed,
          )
        ).traction;
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
