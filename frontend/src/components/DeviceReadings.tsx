import type { RobotStatus } from "../types/api";
import { Card, Reading, dateTime } from "./ui";
export function DeviceReadings({ robot }: { robot: RobotStatus | null }) {
  const device = robot?.device;
  if (!device) return null;
  const reading = robot?.telemetry.device_reading;
  const adc = reading?.sensors.soil_moisture_adc;
  const battery = reading?.sensors.battery;
  const stale = reading?.freshness === "stale";
  return (
    <Card title="Datos del vehículo en pruebas">
      <p>
        {robot?.connection === "diagnostic_online"
          ? "Conexión establecida. Movimiento no disponible durante las pruebas."
          : "Robot desconectado. Comprueba la conexión."}
      </p>
      {!reading ? (
        <p>Esperando datos del sensor.</p>
      ) : (
        <>
          {stale && <p role="status">Última lectura desactualizada.</p>}
          {adc && (
            <>
              <Reading
                label="Lectura del sensor de suelo"
                value={adc.status === "valid" ? adc.value : null}
                unit="ADC"
                stale={stale}
                note="Lectura sin calibrar"
              />
              <p>
                {adc.status === "error" || adc.status === "invalid"
                  ? "No se pudo obtener una lectura válida del suelo."
                  : adc.status === "unavailable"
                    ? "Sensor de suelo no disponible."
                    : "Esta lectura todavía no representa un porcentaje de humedad."}
              </p>
            </>
          )}
          {battery && (
            <Reading
              label="Tensión de batería"
              value={battery.status === "valid" ? battery.voltage_v : null}
              unit="V"
              stale={stale}
              note="Tensión recibida; no estima la carga"
            />
          )}
          <p>Recibida: {dateTime(reading.received_at)}</p>
          <p>
            {reading.measured_at
              ? `Medida: ${dateTime(reading.measured_at)}`
              : "Fecha de medición no informada por el sensor."}
          </p>
          <p>
            Lecturas recibidas en diagnóstico. Se conservan por separado de tus
            muestras NPK.
          </p>
        </>
      )}
      {!!device.errors?.length && (
        <p role="alert">
          El vehículo comunicó un problema. Revisa el equipo antes de continuar.
        </p>
      )}
      <details>
        <summary>Diagnóstico de conexión</summary>
        <pre>{JSON.stringify({ device, reading }, null, 2)}</pre>
      </details>
    </Card>
  );
}
