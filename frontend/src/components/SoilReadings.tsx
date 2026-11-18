import { Reading } from "./ui";
import type { RobotStatus } from "../types/api";

export interface NutrientReading {
  name: string;
  value: number;
  unit: string;
  source: "simulated" | "real";
}

export function exampleNutrients(seed: number): NutrientReading[] {
  let state = seed >>> 0;
  function sample(min: number, max: number) {
    state = (Math.imul(1664525, state) + 1013904223) >>> 0;
    return min + Math.floor((state / 4294967296) * (max - min + 1));
  }
  return [
    {
      name: "Nitrógeno",
      value: sample(15, 55),
      unit: "mg/kg",
      source: "simulated",
    },
    {
      name: "Potasio",
      value: sample(70, 220),
      unit: "mg/kg",
      source: "simulated",
    },
  ];
}
function sessionSeed() {
  const explicit = new URLSearchParams(location.search).get("semilla");
  const saved = explicit ?? sessionStorage.getItem("semi-nutrient-seed");
  const seed =
    saved && /^\d{1,10}$/.test(saved) && Number(saved) <= 0xffffffff
      ? Number(saved)
      : crypto.getRandomValues(new Uint32Array(1))[0];
  sessionStorage.setItem("semi-nutrient-seed", String(seed));
  return seed;
}
const examples = exampleNutrients(sessionSeed());

export function soilMessage(robot: RobotStatus | null) {
  const reading = robot?.telemetry.device_reading;
  const adc = reading?.sensors.soil_moisture_adc;
  if (!adc || adc.status === "unavailable") return "Sin lectura";
  if (reading?.freshness === "stale") return "Última lectura desactualizada";
  if (adc.value === 0)
    return "ADC en cero · revisar pin, alimentación y cableado";
  if (adc.status !== "valid" || adc.value == null)
    return "Sensor sin respuesta válida";
  return "Lectura recibida · pendiente de calibración";
}
export function SoilReadings({
  robot,
  nutrients = examples,
}: {
  robot: RobotStatus | null;
  nutrients?: NutrientReading[];
}) {
  const reading = robot?.telemetry.device_reading;
  const adc = reading?.sensors.soil_moisture_adc;
  return (
    <>
      <div className="reading-grid three soil-readings">
        <Reading
          label="Humedad del suelo"
          value={adc?.value}
          unit="ADC"
          note={soilMessage(robot)}
          stale={reading?.freshness === "stale"}
        />
        {nutrients.map((n) => (
          <Reading
            key={n.name}
            label={n.name}
            value={n.value}
            unit={n.unit}
            note={n.source === "simulated" ? "Simulado" : "Lectura del sensor"}
          />
        ))}
      </div>
      {nutrients.some((n) => n.source === "simulated") && (
        <p className="caption">
          Nitrógeno y potasio · Valor de ejemplo. No tenemos un sensor para
          medirlo.
        </p>
      )}
    </>
  );
}
