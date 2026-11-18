import { createContext, useContext } from "react";
import type { Source } from "./types/api";
export interface RuntimeProfile {
  mode: "operational" | "demonstration";
  dev_tools: boolean;
  device_integration?: "disabled" | "diagnostic";
  lidar_source: Source;
  npk_capture: boolean;
  physical_control: boolean;
}
export const RuntimeContext = createContext<RuntimeProfile>({
  mode: "operational",
  dev_tools: false,
  lidar_source: "real",
  npk_capture: false,
  physical_control: false,
});
export const useRuntime = () => useContext(RuntimeContext);
