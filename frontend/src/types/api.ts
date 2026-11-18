export type Scenario =
  "connected" | "disconnected" | "no_data" | "error" | "stale";
export type Action = "forward" | "backward" | "left" | "right" | "stop";
export type Speed = "low" | "medium";
export type Source = "mock" | "replay" | "real";
export interface Envelope<T> {
  schema_version: "1.0";
  mode: "operational" | "demonstration";
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
  freshness: "fresh" | "stale" | "unknown";
  calibration: string;
  position_method: "none" | "manual_schematic";
  x: number | null;
  y: number | null;
}
export interface ControlState {
  action: Action | null;
  speed: Speed;
  epoch: number;
  window_id: string;
  window_valid_for_ms: number;
  command_ttl_ms: number;
  owner: string | null;
}
export interface DeviceReading {
  message_id: string;
  sampling_point_id: number | null;
  source: "real";
  measured_at: string | null;
  received_at: string;
  age_ms: number | null;
  freshness: "fresh" | "stale";
  sensors: {
    soil_moisture_adc?: {
      value: number | null;
      adc_max?: number | null;
      status: "valid" | "invalid" | "error" | "unavailable";
      sensor_id?: string;
    };
    battery?: {
      voltage_v: number | null;
      status: "valid" | "invalid" | "error" | "unavailable";
      sensor_id?: string;
    };
  };
}
export interface RobotStatus {
  diagnostics?: {
    integration: "disabled" | "diagnostic";
    registered: boolean;
    credential_configured: boolean;
    authentication: string;
    reason: string;
    status_age_ms: number | null;
    telemetry_age_ms: number | null;
  };
  device?: {
    device_id: string;
    firmware: string | null;
    last_seen: string | null;
    age_ms: number | null;
    integration: "diagnostic";
    authorization: { telemetry: boolean; motion: false };
    errors: string[] | null;
  } | null;
  surface_trial?: { state: string; blocked: boolean; source: "simulation" };
  source: Source;
  hardware_connected: boolean;
  connection:
    | "simulated_online"
    | "simulated_offline"
    | "disconnected"
    | "diagnostic_online";
  scenario: Scenario;
  state:
    | "stopped_simulated"
    | "moving_simulated"
    | "fault"
    | "unavailable"
    | "diagnostic";
  control: ControlState;
  capabilities: {
    manual_control: boolean;
    npk_capture: boolean;
    physical_motion: false;
    camera: false;
    ambient: false;
    inclination: false;
  };
  telemetry: {
    device_reading?: DeviceReading;
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
  acquisition?: {
    state:
      | "not_detected"
      | "usb_unidentified"
      | "usb_detected"
      | "waiting"
      | "active"
      | "interrupted"
      | "stale"
      | "error"
      | "unknown";
    selected_port: string | null;
    usb_detected: boolean | null;
    sensor_identified: boolean | null;
    reader_running: boolean | null;
    reader_age_ms: number | null;
    inventory_status: string;
    ports: { port: string; description: string; usb: boolean }[];
    reader_start_authorized: boolean;
  };
  sensor_id: string;
  captured_at: string | null;
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
  freshness: "fresh" | "stale" | "unknown";
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
  mode: "operational" | "demonstration";
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
