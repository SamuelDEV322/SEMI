import { api } from "../services/api";
import { useRuntime } from "../Runtime";
import { useHeldActuator } from "./useHeldActuator";
import { createSessionId } from "../services/session";
import type { RackStatus } from "../types/api";

export function useRackControl(rack: RackStatus | undefined, online: boolean) {
  const runtime = useRuntime();
  return useHeldActuator<"up" | "down">({
    demo: runtime.mode === "demonstration",
    enabled: online,
    lease: rack?.control || null,
    send: async (action, session_id, seq, lease) => {
      const ack = await api.rackCommand({
        domain: "rack",
        mode: "demonstration",
        action,
        device_id: rack?.device_id || "",
        request_id: createSessionId(),
        session_id,
        seq,
        max_duration_ms: action === "stop" ? 0 : 450,
        ...lease,
      });
      if (!ack.rack.control) throw new Error("Rack lease unavailable");
      return ack.rack.control;
    },
  });
}
