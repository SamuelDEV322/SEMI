# Gate 5A — Contrato ESP32–Django v1.0

Fecha de revisión: 17 de noviembre de 2026. Contrato implementado y probado con clientes sintéticos; sin dispositivo físico conectado. No modifica el firmware del equipo.

## Decisión de arquitectura

Se conserva React → HTTP/DRF → servicios → SQLite. El ESP32 inicia peticiones HTTP hacia Django en la LAN. No hay apertura de USB, conexión saliente a placas, MQTT, broker externo ni workers en memoria. La API web conserva `schema_version`, `mode`, `server_time`, `data`.

`SEMI_MODE` mantiene `demonstration|operational` por compatibilidad con Gate 4. No representa una autorización de movimiento. La nueva configuración `SEMI_DEVICE_INTEGRATION` solo acepta `disabled` (predeterminado) o `diagnostic`. El estado futuro de operación física no está implementado ni es un valor admisible. No existe una variable que permita activarlo.

En demostración se utilizan los proveedores existentes y se rechazan las entradas de dispositivo, incluso si se configura diagnostic. Mock/replay sintéticos de LiDAR se conservan como herramientas explícitas anteriores. Se rechaza al iniciar la combinación demonstration + LiDAR real; la lectura USB real sigue disponible en el perfil legacy operational, sin activar motores. Esta restricción nueva impide mezclar adquisición física con la demostración. En modo legacy operational + diagnostic, el proveedor Esp32DiagnosticProvider proyecta mensajes autenticados al contrato de consulta de la UI. Todas las capacidades de movimiento siguen deshabilitadas.

## Rutas existentes y compatibilidad

| Ruta | Estado actual |
|---|---|
| GET /api/health/ | Sobre anterior; agrega `device_integration: disabled|diagnostic`; physical_control continúa false |
| GET /api/robot/status/ | Contrato anterior; agrega conexión diagnostic_online, estado diagnostic y objeto device opcional. control.action continúa null en diagnóstico |
| POST /api/control/command/ | Simulador en demonstration; cualquier control físico sigue rechazado. No alimenta el endpoint de dispositivo |
| GET /api/measurements/latest/ | Muestras agrícolas existentes; no convierte ADC en porcentaje ni en Sample |
| GET /api/measurements/history/ | Historial agrícola existente, sin mezclar telemetría cruda |
| GET/POST /api/npk/samples/ | Lectura conservada; escritura pública física sigue prohibida |
| /api/demo/* y setup(action=demo) | Solo desarrollo explícito; no reciben telemetría real |
| POST /api/measurements/capture/ | No hay captura física NPK implementada; responde indisponibilidad |

## Registro y autenticación

Un operador registra localmente un Device con ID estable (1–64 letras, números, guion o guion bajo), cafetal no demostrativo y sesión UUID generada por Django. Un cafetal admite como máximo un dispositivo habilitado. No hay registro anónimo por HTTP. La sesión identifica una época de secuencias, no una credencial.

Cabeceras obligatorias en **todas** las rutas /api/device/:

- `X-SEMI-Device-ID`: ID registrado y habilitado.
- `X-SEMI-Device-Token`: secreto por dispositivo obtenido de SEMI_DEVICE_TOKENS en el entorno privado del backend.

Los tokens se comparan con hmac.compare_digest sobre digest SHA-256. No se almacenan en SQLite ni se envían a React. La configuración acepta un objeto JSON ID→token con tokens de 32 a 512 caracteres. `.env.example` contiene un objeto vacío. Ningún ejemplo incorpora un token real. Las pruebas generan credenciales efímeras.

Dispositivo inexistente, credencial ausente/errónea, token no configurado o dispositivo deshabilitado producen el mismo 401 `device_auth_failed`, sin revelar cuál condición falló. Una credencial válida con integración deshabilitada o modo demonstration recibe 403 `integration_disabled`.

Solo estas vistas marcadas de dispositivo sustituyen CSRF por autenticación por cabeceras. El middleware no concede excepciones por prefijo ni por la presencia de una cabecera. Los formularios del navegador mantienen cookie/token y validación de Origin. No se habilita CORS global. La separación sigue el [modelo de autenticación de DRF](https://www.django-rest-framework.org/api-guide/authentication/).

El token identifica al emisor, pero no demuestra calibración, veracidad física ni firma criptográfica de cada sensor. HTTP no cifra el token; usar únicamente una red de confianza y no exponer el servidor a Internet. HTTPS/autenticación del operador son trabajo posterior antes de ampliar el acceso.

## Sobre de respuesta

Ejemplo estructural ficticio, sin lectura física:

```json
{"schema_version":"1.0","mode":"operational","server_time":"2026-11-17T12:00:00Z","data":{"action":"stop","motion_enabled":false}}
```

Las respuestas nuevas de error conservan el mismo sobre y agregan `error: {code, detail}`. `data` siempre contiene STOP/motion_enabled=false ante un error de dispositivo; un cliente no debe tratar un HTTP no exitoso como autorización. Los errores existentes del navegador conservan su formato anterior.

Las respuestas de dispositivo llevan Cache-Control: private, no-store. Los POST requieren application/json, versión exacta "1.0" y como máximo 32 KiB. Se rechazan campos desconocidos, claves JSON duplicadas, números no finitos y tipos incompatibles. No convertir booleanos o texto numérico en ADC/secuencias. El origen `real` lo asigna el servidor por el canal autenticado; no se admite un campo source manipulable en el cuerpo.

## POST /api/device/telemetry/

| Campo | Regla |
|---|---|
| schema_version | string, exactamente "1.0", obligatorio |
| session_id | UUID de sesión vigente, obligatorio |
| message_id | UUID único por dispositivo/canal; conservar en reintentos |
| seq | entero JSON 0..2147483647, estrictamente creciente por canal/sesión |
| measured_at | fecha ISO 8601 con zona o null/ausente; nunca se inventa. Se rechaza más de 30 s en el futuro |
| sampling_point_id | entero positivo o null/ausente; debe pertenecer al cafetal asignado y no ser demo |
| sensors | objeto no vacío con las lecturas admitidas siguientes |

Sensores admitidos:

| Objeto/campo | Regla |
|---|---|
| soil_moisture_adc.value | entero 0..65535 o null; cero es una lectura, no ausencia |
| soil_moisture_adc.adc_max | resolución máxima declarada 1..65535; obligatoria si existe valor; puede faltar/ser null cuando no hay valor |
| soil_moisture_adc.status | valid, invalid, error o unavailable; valid exige valor y rango dentro de adc_max |
| soil_moisture_adc.sensor_id | string opcional, máximo 80; no inventar una referencia no conocida |
| battery.voltage_v | número finito 0..100 o null; valid exige número. Límite de plausibilidad del transporte, no aprobación eléctrica |
| battery.status / sensor_id | mismas reglas de estado/identificación |

No hay campo de porcentaje de humedad, carga de batería ni NPK en esta revisión. La calibración y el modelo NPK son desconocidos: se rechazan esos campos en lugar de inventarlos. Una lectura ADC válida significa estructura/rango válidos, no validez agronómica. Un estado invalid/error puede conservar su valor original si es representable y está dentro del rango; la UI no lo presenta como lectura válida.

Ejemplo **exclusivamente ficticio de contrato**; no enviarlo como adquisición real a la base habitual:

```json
{
  "schema_version":"1.0",
  "session_id":"11111111-1111-4111-8111-111111111111",
  "message_id":"22222222-2222-4222-8222-222222222222",
  "seq":0,
  "measured_at":null,
  "sampling_point_id":1,
  "sensors":{"soil_moisture_adc":{"value":1700,"adc_max":4095,"status":"valid","sensor_id":"ejemplo-sintetico"}}
}
```

El servidor guarda el cuerpo JSON aceptado, sin recalibrar sus valores, el hash canónico, fecha de recepción propia, fecha de medición si existe, sesión, secuencia y referencia de lugar. Se conserva la información original JSON; no se conservan sus espacios ni el orden textual de claves. No se crea Sample ni SystemEvent por cada paquete.

201: primera recepción. `data` incluye device_id, message_id, seq, received_at, measured_at, sampling_point_id, source="real", duplicate=false y payload original. 200: reintento idéntico, duplicate=true y fecha original. El reintento no renueva heartbeat. Mismo ID y distinto contenido: 409 message_conflict. ID nuevo con secuencia antigua/repetida: 409 sequence_old. No hay escrituras parciales cuando se rechaza un lugar o una secuencia.

GET /api/device/telemetry/?schema_version=1.0&limit=20 permite al dispositivo autenticado consultar sus últimas lecturas persistidas (1..100). No lee otros dispositivos. Se conservan mensajes de sesiones anteriores como historia, pero no se proyectan como lectura actual del nuevo arranque.

## POST /api/device/status/

Comparte schema_version/session_id/message_id/seq/measured_at. Su secuencia es independiente del canal telemetry. Todos los demás campos pueden faltar; no se inventan:

| Campo | Tipo/regla |
|---|---|
| firmware | string máximo 80 o null |
| uptime_ms | entero 0..9007199254740991 o null |
| firmware_state | booting, ready, error o null |
| capabilities | objeto con telemetry/motion booleanos o null; declaraciones del firmware, no permisos |
| errors | lista de hasta 10 textos, máximo 160 cada uno |
| reported_motion | unknown, stopped o moving; declaración sin verificación física |
| ack | opcional: command_id UUID, seq y result="received" |

El ack solo admite la última respuesta STOP de la sesión y aún vigente. `received` no significa aplicada ni robot detenido. Nunca se transforma en control.action=stop ni en physical_stop_verified=true. No se admite un ack de movimiento aplicado. Un heartbeat con firmware_state=error mantiene la evidencia de comunicación y conserva los errores, pero nunca habilita movimiento.

## GET /api/device/commands/next/

Parámetros obligatorios: schema_version=1.0, session_id vigente, request_id UUID y seq de consulta monótona 0..2147483647. Se rechazan claves desconocidas o repetidas.

No existe cola de movimientos ni endpoint para insertarla. StopCommandBroker solo conserva la última respuesta STOP del dispositivo. Una petición nueva incrementa command.seq y crea command_id; no actualiza last_seen, porque consultar órdenes no equivale a enviar estado/lecturas. Su única respuesta exitosa tiene:

```json
{
  "device_id":"ejemplo",
  "session_id":"11111111-1111-4111-8111-111111111111",
  "command_id":"33333333-3333-4333-8333-333333333333",
  "seq":1,
  "action":"stop",
  "motion_enabled":false,
  "authorization":"diagnostic_only",
  "reason":"physical_motion_not_authorized",
  "expires_at":"2026-11-17T12:00:00.450Z",
  "valid_for_ms":450,
  "duplicate":false
}
```

Ejemplo ficticio. El plazo de 450 ms es una vigencia de recepción de esta respuesta de diagnóstico, **no** un valor de seguridad validado para motores. Reintentar la última petición idéntica devuelve la misma respuesta con el plazo restante; no lo prolonga. Tras vencer devuelve 409 command_expired y STOP desautorizado. Una consulta anterior a la última se rechaza por secuencia. No se mantiene historia de todas las consultas ni una orden pendiente reejecutable. El request_id es correlación; sesión y secuencia determinan el orden.

El firmware futuro debe medir plazos con reloj monotónico local, considerar latencia de ida/vuelta y volver a STOP ante cualquier error, ausencia, JSON inválido, versión distinta o desautorización. Esta entrega no añade ni conecta funciones avanzar/retroceder/girar/cremallera. No invocar actuadores desde este contrato durante Gate 5.

## Sesiones, reinicios y concurrencia

La sesión y las secuencias se guardan en SQLite. Un reinicio de Django no borra identificadores ni convierte una petición antigua en una orden nueva. Una reconexión conserva la sesión y continúa secuencias; no hay movimiento que pueda reanudarse. Si el ESP32 reinicia sus contadores, el operador debe ejecutar register_device --reset-session y comunicar la nueva sesión al firmware. Las sesiones anteriores quedan invalidadas y las lecturas previas se conservan. No resetear contadores silenciosamente ni registrar un dispositivo nuevo por cada reconexión Wi-Fi.

La ingesta inicia una transacción con una escritura sobre Device antes de leer/comprobar secuencias e idempotencia. Así se serializan escritores de SQLite incluso entre procesos; no se confía en un diccionario global ni en select_for_update, que [no bloquea filas en SQLite](https://docs.djangoproject.com/en/5.2/ref/databases/#queryset-select-for-update-not-supported). Las restricciones únicas de SQLite refuerzan identidad/secuencia. Ante bloqueo del almacenamiento se devuelve 503 storage_busy para reintentar el mismo paquete, no otro ID.

## Estados de la UI y vencimientos informativos

- Sin registro/mensaje: desconectado; sin datos, sin porcentaje o batería fabricados.
- Mensaje de estado/telemetría nuevo autenticado: diagnostic_online, solo lectura. No equivale a validación física realizada por el equipo.
- Sin comunicación válida durante 15 s: desconectado. Un reloj de recepción en el futuro también deja de afirmar conexión.
- Telemetría con antigüedad mayor a 60 s: desactualizada. Se considera tanto recepción como medición cuando existe; un sensor que retransmite una lectura antigua no la hace nueva.
- Error/invalid/unavailable: conservar la lectura/estado original y no usar el número como válido. No recurrir al mock.

15 s/60 s son indicadores de UX; nunca protecciones mecánicas. Las lecturas actuales se filtran por la sesión activa y por cafetal. Las muestras NPK conservan su propio contrato y antigüedad.

## Errores y política de fallos

| Caso | Respuesta/acción |
|---|---|
| Wi-Fi o backend inaccesible | cliente conserva incertidumbre, STOP local futuro; no reenviar movimiento antiguo |
| Dispositivo/credencial inválida | 401 device_auth_failed; no escribir datos |
| Integración deshabilitada | 403 integration_disabled |
| Sesión inválida | 409 session_invalid; revisión local del registro |
| Mensaje repetido idéntico | 200 duplicate, sin nueva fila ni renovación de conexión |
| ID repetido con contenido diferente | 409 message_conflict |
| Secuencia antigua | 409 sequence_old |
| Orden vencida | 409 command_expired; no reactivar |
| Ack desconocido | 409 command_unknown |
| Punto ajeno/inexistente/demo | 400 point_not_owned; sin escrituras parciales |
| JSON inválido/NaN/claves repetidas | 400 parse_error |
| Versión ausente/distinta | 400 schema_version_unsupported |
| Campos/rangos inválidos | 400 validation_error |
| Payload grande | 413 payload_too_large |
| Tipo de contenido incorrecto | 415 unsupported_media_type |
| Almacenamiento ocupado | 503 storage_busy; reintento idempotente |
| Dispositivo conectado sin autorización | lectura/estado disponibles; STOP/motion_enabled=false; mandos web bloqueados |
| Sensor sin lectura/antiguo/error | valor ausente/obsoleto/error explícitos; nunca cero ni fallback |
| Reinicio/reconexión | estado durable; sesiones/secuencias anteriores no se rehabilitan |

## Compatibilidad con el equipo mecatrónico

Se encontró y leyó `C:/Users/jh818/Downloads/SemiApiBridge.h`, SHA-256 `8771f64a467cc9bd1d13eff4af8c8adbbe7dc450e3b000f45b70ebd07a756d71`. Es una propuesta separada que declara no estar integrada, no define pines ni motores y depende de Arduino-ESP32/ArduinoJson 7. No se editó, compiló, copió al repositorio ni conectó a funciones de locomoción.

Se conservan /api/device/commands/next/, /api/device/telemetry/, X-SEMI-Device-ID y X-SEMI-Device-Token, además del sobre y `mode=operational` que valida el bridge. La compatibilidad de payload **requiere adaptación explícita del bridge por el equipo**:

| Propuesta del header | Contrato Gate 5 | Motivo |
|---|---|---|
| device_id en el cuerpo | identidad en cabecera autenticada, registro y cafetal del servidor | Evitar identidad/asociación manipulable |
| reading_id libre | message_id UUID estable por paquete/canal | Idempotencia definida y validable |
| soil_adc_raw plano (0..4095) | sensors.soil_moisture_adc con value, adc_max y status | Conservar ADC sin asumir resolución/calibración |
| calibrated=false | lectura cruda por contrato, sin campo de porcentaje | No declarar una calibración inexistente |
| source=real enviado por cliente | source asignado por Django | No confiar en una etiqueta del emisor |
| sin versión/sesión/secuencia en POST | schema_version, session_id y seq obligatorios | Reintentos, reconexión y protección contra paquetes antiguos |
| sin measured_at | puede permanecer ausente/null | El ESP32 no necesita inventar un reloj calendario |
| GET commands sin parámetros | versión/sesión/request_id/seq | Correlación y orden de consultas |
| armed=true, epoch, speed_pwm, ttl_ms para aceptar movimiento | action=stop, motion_enabled=false, seq, command_id, valid_for_ms | Gate 5 no implementa movimientos ni PWM. No se proporciona armed=true |
| token de al menos 16 caracteres | configuración backend exige al menos 32 | Usar secreto fuerte; el mínimo permisivo del header no basta |
| no heartbeat de dispositivo | POST /status con identificación de firmware opcional | Diferenciar consultar health de recibir estado del dispositivo |
| sin cola/reintento persistente local de lectura | repetir ID/cuerpo tras timeout | Evitar perder/duplicar una misma adquisición |

El JSON plano actual de sendSoilReading recibe 400 schema_version_unsupported, no se inserta parcialmente ni se transforma silenciosamente. Una prueba de regresión reproduce ese cuerpo ficticio. Agregar solamente schema_version tampoco basta: deben revisarse conjuntamente sesión, secuencia y forma de sensores. No se añadió un adaptador permisivo que invente estos campos.

El header consulta health cada 2500 ms y utiliza timeout HTTP de 350 ms. Ese sondeo demuestra que Django responde, pero no constituye un heartbeat recibido por Django. Sus operaciones HTTP son síncronas y su propio comentario exige un supervisor independiente. Validar latencia/jitter y política de reintento antes de acordar frecuencias; no deducir que 350/450 ms son valores de frenado seguros.

Con physical_control=false, fetchCommand retorna false/STOP sin consultar la ruta de órdenes. Incluso si se forzase esa consulta sin adaptación, no recibiría armed=true ni una estructura de movimiento aceptable. Esto es revisión de código, no una prueba de compilación/ejecución del ESP32. El callback forceStop del header no se conectó a ningún actuador en esta ejecución.

La siguiente revisión debe realizarse sobre una propuesta separada del equipo, preservando el sketch mecatrónico: mantener los campos nuevos, evitar que la recepción de una orden reactive movimiento y ejecutar el watchdog en el controlador local. Ningún cambio del header se hizo durante Gate 5.
