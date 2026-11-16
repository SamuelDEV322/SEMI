import type { Sample } from "./api";
export interface Sector {
  id: number;
  name: string;
  archived: boolean;
  historical_surface: boolean;
  point_count: number;
  has_history: boolean;
}
export interface SetupPoint {
  id: number;
  code: string;
  name: string;
  x: number | null;
  y: number | null;
  zone: number | null;
  latest_sample: Sample | null;
}
export interface SetupPlot {
  id: number;
  name: string;
  crop: string;
  demo: boolean;
  step: number;
  completed: boolean;
  zones: Sector[];
  points: SetupPoint[];
}
export interface SurfaceTrial {
  state: string;
  conservative: boolean;
  source: "simulation";
  physical_detection: false;
}
export type SetupAction = (
  action: string,
  extra?: Record<string, unknown>,
) => Promise<SetupPlot | null>;
