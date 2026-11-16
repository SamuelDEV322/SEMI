import type {
  Envelope,
  Command,
  CommandAck,
  RobotStatus,
  Sample,
  Scan,
  Scenario,
  SamplingPoint,
} from "../types/api";
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code: string,
  ) {
    super(message);
  }
}
let csrf: Promise<string> | null = null;
export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 3500);
  try {
    const response = await fetch(`/api/${path}`, {
      ...init,
      signal: controller.signal,
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        ...(localStorage.getItem("semi-plot")
          ? { "X-SEMI-Plot": localStorage.getItem("semi-plot")! }
          : {}),
        ...init.headers,
      },
    });
    let body: unknown;
    try {
      body = await response.json();
    } catch {
      throw new ApiError(
        "Respuesta inválida del servidor.",
        response.status,
        "invalid_json",
      );
    }
    const value = body as { error?: { detail?: unknown; code?: string } };
    if (!response.ok)
      throw new ApiError(
        typeof value.error?.detail === "string"
          ? value.error.detail
          : JSON.stringify(value.error?.detail || "Error de API"),
        response.status,
        value.error?.code || "request_error",
      );
    const envelope = body as Envelope<T>;
    if (
      envelope.schema_version !== "1.0" ||
      !["operational", "demonstration"].includes(envelope.mode) ||
      !("data" in envelope)
    )
      throw new ApiError(
        "Contrato o modo de API incompatible.",
        502,
        "contract_error",
      );
    return envelope.data;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(
      "No hay conexión con el sistema. Intenta de nuevo.",
      0,
      "network_error",
    );
  } finally {
    clearTimeout(timer);
  }
}
async function post<T>(
  path: string,
  data: unknown,
  method: "POST" | "PATCH" = "POST",
) {
  if (!csrf)
    csrf = request<{ csrf_token: string }>("health/")
      .then((v) => v.csrf_token)
      .catch((error) => {
        csrf = null;
        throw error;
      });
  const token = await csrf;
  try {
    return await request<T>(path, {
      method,
      headers: { "X-CSRFToken": token },
      body: JSON.stringify(data),
    });
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) csrf = null;
    throw error;
  }
}
export const api = {
  runtime: () => request<import("../Runtime").RuntimeProfile>("health/"),
  trial: () => request<import("../types/setup").SurfaceTrial>("demo/surface/"),
  setTrial: (data: object) =>
    post<import("../types/setup").SurfaceTrial>("demo/surface/", data),
  pointHistory: (id: number | undefined, period: string) => {
    if (id === undefined) return Promise.resolve([] as Sample[]);
    const query = new URLSearchParams({ limit: "100", point: String(id) });
    if (period !== "all")
      query.set(
        "since",
        new Date(Date.now() - Number(period) * 3600000).toISOString(),
      );
    return request<Sample[]>(`measurements/history/?${query}`);
  },
  robot: () => request<RobotStatus>("robot/status/"),
  latest: () => request<Sample | null>("measurements/latest/"),
  history: () => request<Sample[]>("measurements/history/?limit=100"),
  lidar: () => request<Scan>("lidar/latest/"),
  command: (command: Command) => post<CommandAck>("control/command/", command),
  scenario: (scenario: Scenario) =>
    post<RobotStatus>("demo/scenario/", { scenario }),
  capture: (point_label: string, sampling_point?: number) =>
    post<Sample>("measurements/capture/", { point_label, sampling_point }),
  points: () => request<SamplingPoint[]>("sampling-points/"),
  updatePoint: (
    id: number,
    point: { position_method: string; x: number | null; y: number | null },
  ) => post<SamplingPoint>(`sampling-points/${id}/`, point, "PATCH"),
  createPoint: (point: {
    name: string;
    position_method: string;
    x: number | null;
    y: number | null;
  }) => post<SamplingPoint>("sampling-points/", point),
  saveSample: (sample: Omit<Sample, "id" | "freshness" | "calibration">) =>
    post<Sample>("npk/samples/", sample),
};

export const setupAction = (data: object) =>
  post<import("../types/setup").SetupPlot>("setup/", data);
