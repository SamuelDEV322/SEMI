import { manual, type ManualChannel } from "../services/manual";
import { api } from "../services/api";
import { useRuntime } from "../Runtime";
import { useHeldActuator } from "./useHeldActuator";
import { createSessionId } from "../services/session";
import type { RackStatus } from "../types/api";

export function useRackControl(
  rack: RackStatus | undefined,
  online: boolean,
  key: string,
  channel?: ManualChannel,
) {
  const runtime = useRuntime();
  return useHeldActuator<"up" | "down">({
    demo: runtime.mode === "demonstration",
    enabled: online,
    physical: !!channel && !!key,
    lease: channel || rack?.control || null,
    send: async (action, session_id, seq, lease) => {
      if (runtime.mode === "operational")
        return (await manual(key, "rack", action, lease, session_id, seq)).rack;
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
