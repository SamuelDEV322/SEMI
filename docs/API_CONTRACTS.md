> Actualización 2026-11-16: el perfil predeterminado es operativo, sin fuentes sintéticas ni cambio de origen desde UI/API. Consultar [OPERATING_PROFILE.md](OPERATING_PROFILE.md) para el contrato vigente y los límites físicos. Las secciones de Gates anteriores conservan su contexto histórico.

> Actualización Gate 2: consultar [GATE2.md](GATE2.md). El contenido Gate 1 se conserva como antecedente.

# API v1.0 — Gate 1

Base `/api/`. JSON UTF-8. Tiempos ISO 8601 con zona. Valores numéricos finitos; ausencia = null, nunca cero automático. Solo modo `demonstration`.

## Sobre

```json
{"schema_version":"1.0","mode":"demonstration","server_time":"2026-11-15T19:00:00+00:00","data":{}}
```

Todas las fechas/valores de los ejemplos de este documento son ilustrativos. Errores de API:

```json
{"mode":"demonstration","error":{"code":"physical_control_forbidden","detail":"Gate 1 solo admite comandos de demostración."}}
```

Un error de validación puede usar un objeto de campos en `detail`. Los errores HTTP 404 fuera de las rutas API y errores internos de Django no tienen garantizado este sobre; el cliente presenta un error de respuesta inválida si no recibe JSON.

## Endpoints

| Método / ruta | data / comportamiento |
|---|---|
| GET health/ | estado de DB, `physical_control:false` y token CSRF |
| GET robot/status/ | estado del simulador, capacidades, batería mock, ventana de mando y últimos 8 eventos |
| GET measurements/latest/ | Sample o null; escenario sin datos/desconectado = null |
| GET measurements/history/?limit=100 | Array de Sample, más recientes primero |
| GET npk/samples/?limit=100 | Mismas muestras de contacto agronómico |
| POST npk/samples/ | Crea muestra mock validada; devuelve 201 |
| GET lidar/latest/ | Último escaneo mock generado en memoria; sin persistir puntos |
| POST control/command/ | Solo órdenes simuladas; no acciona hardware |
| POST demo/scenario/ | Cambia escenario y detiene/invalida el mando previo |
| POST demo/capture/ | Genera una muestra mock con etiqueta; 201 y persistencia SQLite |

`limit`: entero de 1 a 200. No existe paginación completa en Gate 1; se limita explícitamente el historial. Los escenarios sin datos actuales no borran el historial.

## Sample

```json
{
  "id":1,"captured_at":"2026-11-15T19:00:00Z","point_label":"Zona A",
  "nitrogen":34,"phosphorus":18,"potassium":87,"soil_moisture":42,
  "npk_unit":"mg/kg","moisture_unit":"%","status":"valid","source":"mock",
  "freshness":"fresh","calibration":"demonstration_not_agronomically_validated",
  "position_method":"manual_schematic","x":22,"y":65
}
```

N/P/K/humedad: `number|null`. Al menos una variable en POST debe tener valor. NPK no negativo; humedad de 0 a 100; NaN/infinito rechazados. `captured_at` obligatorio y no puede estar más de cinco segundos en el futuro. `status`: valid/invalid. Una muestra válida de demostración no significa precisión agronómica real.

`source` es mock en Gate 1; real/replay rechazados en escrituras. Unidades fijadas por el backend como demostración. `freshness` se calcula con umbral de 300 s; no declara inválidas muestras históricas. Escenario stale fuerza obsolescencia en la última muestra sin alterar el historial guardado.

`position_method=none` exige x/y null. `manual_schematic` exige ambos números entre 0 y 100; son coordenadas adimensionales de un esquema y nunca latitud/longitud. No se admite GNSS ni una posición inferida del LiDAR. Una captura demo nueva conserva posición none.

## Scan

```json
{
  "sensor_id":"mock-rplidar-a1","captured_at":"2026-11-15T19:00:00Z",
  "status":"simulated","source":"mock","unit":"mm","valid":true,
  "freshness":"fresh","angle_convention":"0=forward; clockwise; robot_local",
  "max_range_mm":4000,
  "points":[{"angle_deg":0,"distance":1750,"quality":35,"valid":true}]
}
```

Contrato compartido: source mock/replay/real; la implementación actual solo produce mock. Calidad `integer|null`; distancia `number|null`; validez por escaneo y punto. El radar filtra puntos inválidos y fuera del rango de visualización. El máximo de 4 m es una escala de esta demostración, no una especificación medida del A1. Sin datos: valid=false, status=unavailable, points=[]. Stale: marca y tiempo antiguo explícitos. No implica mapa o posición global.

## Control

Antes de escribir, GET health/ obtiene `csrf_token` y cookie. Enviar `X-CSRFToken` con la cookie del mismo origen. Origin debe pertenecer a los orígenes configurados. Vite conserva el mismo origen hacia el navegador.

GET robot/status/ entrega `control.epoch`, `window_id` y `window_valid_for_ms`. La ventana caduca con reloj monotónico del servidor. El cliente no puede ampliar una ventana cambiando un timestamp.

```json
{"mode":"demonstration","action":"forward","speed":"low","session_id":"779e43d9-f419-4bac-964d-5b22ae62df4a","seq":1,"epoch":0,"window_id":"VENTANA-EMITIDA-POR-ESTADO"}
```

- action: forward/backward/left/right/stop.
- speed: low/medium, demandas normalizadas 0,25/0,50; no m/s ni PWM físico.
- session_id UUID, seq entero creciente por sesión, epoch de estado.
- Solo un operador mantiene movimiento. STOP puede solicitarlo cualquier sesión demo y no depende de tener ventana vigente.
- Vigencia máxima de movimiento: 450 ms o fin de ventana, lo que ocurra primero.
- STOP incrementa época y vacía ventanas; una orden previa no reactiva movimiento.
- Reconectar o cambiar escenario conserva STOP.
- ACK: `result=applied_simulated`, `hardware_acted=false`, `track_demand` y nuevo estado de control.

## Errores

| HTTP | Casos |
|---|---|
| 400 | Campos, dirección, velocidad, fecha, posición o límite inválidos |
| 403 | CSRF ausente/origen no permitido; modo físico o muestra real |
| 409 | Secuencia antigua, época antigua, ventana vencida, otro operador; captura en escenario no disponible |
| 429 | Límite de sesiones de simulación alcanzado |
| 503 | Enlace simulado desconectado o error de adquisición |

## Escenarios

POST demo/scenario/ con `{"scenario":"connected"}`. Valores: connected, disconnected, no_data, stale, error. El estado de robot sigue consultable incluso en error. Las fuentes no se anuncian como hardware conectado. POST demo/capture/ acepta `{"point_label":"Punto 01"}` solo en connected.


## Contratos Gate 3

Se añade GET/POST /api/setup/ y la cabecera X-SEMI-Plot. Ver la tabla de acciones y errores en GATE3.md. Puntos, capturas e historial se filtran por terreno; el contexto por defecto es el principal. SamplingPoint incorpora code, zone y display_name de solo lectura. Los comandos siguen exclusivamente en demostración y pueden recibir 409 surface_demo_stop. No hay geofence ni clasificación física.


## Evolución de contrato Gate 4

GET/POST /api/setup/ usa ahora etapas 1–4 y sectores por nombre. Se retiran category/surface/conservative del JSON agrícola; los tipos y consumidores se actualizaron. Acciones: sector, sector_delete (confirmed=true, solo vacío sin referencias), sector_archive, sector_restore, sector_detach (confirmed=true). point acepta x/y null y sector opcional; el contrato de puntos incluye sector_history. GET/POST /api/demo/surface/ gestiona exclusivamente ensayos simulados. Ver campos, alias compatibles, errores y ejemplos de flujo en GATE4.md. No cambia el contrato de mando físico: permanece prohibido con 403.
