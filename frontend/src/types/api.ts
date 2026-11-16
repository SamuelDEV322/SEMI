export type Scenario =
  "connected" | "disconnected" | "no_data" | "error" | "stale";
export type Action = "forward" | "backward" | "left" | "right" | "stop";
export type Speed = "low" | "medium";
export type Source = "mock" | "replay" | "real";
export interface Envelope<T> {
  schema_version: "1.0";
  mode: "demonstration";
  server_time: string;
  data: T;
}
export interface Sample {
  id: number;
  captured_at: string;
  point_label: string;
  sampling_point: number | null;
  nitrogen: number | null;
  phosphorus: number | null;
  potassium: number | null;
  soil_moisture: number | null;
  npk_unit: string;
  moisture_unit: string;
  status: "valid" | "invalid";
  source: Source;
  freshness: "fresh" | "stale";
  calibration: string;
  position_method: "none" | "manual_schematic";
  x: number | null;
  y: number | null;
}
export interface ControlState {
  action: Action;
  speed: Speed;
  epoch: number;
  window_id: string;
  window_valid_for_ms: number;
  command_ttl_ms: number;
  owner: string | null;
}
export interface RobotStatus {
  surface_trial?: { state: string; blocked: boolean; source: "simulation" };
  source: "mock";
  hardware_connected: false;
  connection: "simulated_online" | "simulated_offline";
  scenario: Scenario;
  state: "stopped_simulated" | "moving_simulated" | "fault";
  control: ControlState;
  capabilities: {
    physical_motion: false;
    camera: false;
    ambient: false;
    inclination: false;
  };
  telemetry: {
    battery: {
      value: number | null;
      unit: string;
      source: Source;
      validity: string;
      freshness: string;
      status: string;
    };
    ambient_temperature: null;
    ambient_humidity: null;
    inclination: null;
  };
  events: {
    id: number;
    created_at: string;
    kind: string;
    message: string;
    source: Source;
  }[];
}
export interface Scan {
  sensor_id: string;
  captured_at: string;
  status:
    | "simulated"
    | "unavailable"
    | "valid"
    | "stale"
    | "disconnected"
    | "no_data"
    | "error";
  age_ms?: number | null;
  error?: string | null;
  source: Source;
  unit: "mm";
  valid: boolean;
  freshness: "fresh" | "stale";
  max_range_mm: number;
  angle_convention: string;
  points: {
    angle_deg: number;
    distance: number | null;
    quality: number | null;
    valid: boolean;
  }[];
}
export interface Command {
  mode: "demonstration";
  action: Action;
  speed: Speed;
  session_id: string;
  seq: number;
  epoch: number;
  window_id: string;
}
export interface CommandAck {
  result: "applied_simulated";
  hardware_acted: false;
  track_demand: [number, number];
  control: ControlState;
}

export interface SamplingPoint {
  sector_history?: { id: number; name: string; archived: boolean }[];
  code?: string;
  zone?: number | null;
  display_name?: string;
  id: number;
  name: string;
  position_method: "none" | "manual_schematic";
  x: number | null;
  y: number | null;
  created_at: string;
  latest_sample: Sample | null;
}
