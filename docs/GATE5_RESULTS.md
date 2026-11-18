# Resultado Gate 5A + Gate 5B

Revisión: 17 de noviembre de 2026. Proyecto existente SEMI, rama main, HEAD c6c6aca. No se creó otro proyecto y no se realizaron commits ni push.

## Resultado

**Implementado:** contratos v1.0, autenticación de dispositivo, registro local, endpoints de diagnóstico, almacenamiento de ADC/voltios/estado sin calibración inventada, idempotencia y secuencias durables, asociación al cafetal, respuestas STOP-only, ampliaciones compatibles de React y configuración disabled/diagnostic. La instalación habitual permanece disabled sin dispositivos ni tokens configurados.

**Probado mediante simulación:** el cliente de test envía mensajes ficticios por el canal real autenticado en bases aisladas. La fuente real identifica el canal de adquisición; no constituye una prueba física. No se insertaron esas fixtures en la SQLite habitual.

**Pendiente de validación física:** ESP32, bridge adaptado, adquisición capacitiva, red, calibración, electrónica, firmware y watchdog local.

**No implementado:** accionamiento de orugas/cremallera, GPIO/PWM, flasheo, navegación, material del suelo, NPK físico o porcentajes derivados. No se abrió USB ni se cambió la integración LiDAR existente.

## Endpoints

| Método | Ruta | Resultado |
|---|---|---|
| GET | /api/device/commands/next/ | STOP con movimiento desautorizado; secuencia/sesión/vigencia persistentes |
| POST | /api/device/telemetry/ | Valida y almacena mensaje original; ADC sin calibrar y tensión opcional |
| GET | /api/device/telemetry/ | Historial autenticado del propio dispositivo, limit 1..100 |
| POST | /api/device/status/ | Heartbeat/firmware/errores y ack de recepción; no confirmación física |
| GET | /api/health/ | Conserva sobre y physical_control=false; agrega device_integration |
| GET | /api/robot/status/ | Estado de diagnóstico y última telemetría por cafetal/sesión |
| POST | /api/control/command/ | Demo conservado; movimiento de diagnóstico rechazado con 403 |

El contrato detallado, JSON, campos, errores y fallbacks están en GATE5A_CONTRACTS.md. La arquitectura, archivos y ejecución están en GATE5B_IMPLEMENTATION.md.

## Arquitectura definitiva de este incremento

ESP32/cliente → autenticación de dispositivo → vistas DRF (gateway HTTP) → DeviceTelemetryService/StopCommandBroker → SQLite. Esp32DiagnosticProvider proyecta lecturas a robot/status y React reutiliza la UI. Los proveedores mock permanecen independientes; no se añade otro broker ni infraestructura.

## Pruebas ejecutadas

| Comprobación | Resultado |
|---|---|
| Línea base Django | 60 aprobadas |
| Línea base navegador | 29 demo + 11 MVP aprobadas |
| Línea base TypeScript/Vite | Compila |
| Django final | 92 aprobadas |
| Navegador diagnóstico | 11 aprobadas |
| Regresión demo Gates 2/4 | 29 aprobadas |
| Regresión MVP sin dispositivo | 11 aprobadas |
| TypeScript/Vite final | Compila |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Black, módulos modificados | Correcto; no se formateó test_gate3.py |
| git diff --check | Correcto |
| SQLite histórica | Filas originales íntegras; integrity_check ok; foreign_key_check vacío |

Las 32 pruebas Django nuevas abarcan autenticación/revocación, CSRF separado, configuración insegura rechazada, originalidad ADC/voltios, ceros/nulos, rangos y tipos, errores JSON, versión, identidad/idempotencia, asociación entre cafetales, sesiones, concurrencia SQLite, obsolescencia, desconexión, TTL con reloj inyectado, ACK sin confirmación física y rechazo del bridge preliminar. Los bloqueos de SQLite se convierten en 503 reintentable; no se asume que una prueba de concurrencia sea un ensayo de carga completo.

Playwright verificó 360, 390, 768 y 1440 px y claro/oscuro, ausencia de desbordamiento horizontal, mandos bloqueados aun con capabilities.motion declarado true, datos ausentes/antiguos/error y ausencia de NPK inventado. Otro proceso Django leyó la misma lectura persistida y sus contadores. La regresión anterior conserva táctil, teclado, cancelaciones y ensayo STOP simulado. Las pruebas no demuestran usabilidad con un agricultor ni comportamiento físico.

Durante el desarrollo se corrigieron el manejo de errores de campos desconocidos, números demasiado grandes y un selector de prueba que confundía el separador de miles con texto dentro del diagnóstico oculto. Los logs finales citados corresponden a ejecuciones aprobadas. Se detuvo únicamente una tarea de formato propia que se había quedado esperando; se repitió satisfactoriamente la comprobación. No se detuvieron servidores ajenos.

## Base y archivos del usuario

Se aplicó devices.0001_initial (dos tablas), sin modificar las tablas agrícolas. Se comparó cada fila anterior por ID y valores: continúan 17 muestras, 9 lugares, 3 terrenos, 4 sectores, 86 eventos y sus referencias. Solo crecen metadatos Django por registrar la app. Las tablas nuevas de la base habitual tienen 0 dispositivos y 0 mensajes; la recepción queda sin configurar. No se ejecutaron semillas en esa base ni se creó una base nueva de producción.

VS Code mostraba test_gate3.py sin guardar. No se guardó ni modificó; los tests utilizan su versión en disco. .django-stub-gen permanece intacto, sin versionar. Firmware y package-lock.json no cambiaron. El checkpoint recuperable sigue siendo el commit existente; no se fabricó un commit nuevo ni un ZIP o copia del proyecto.

## Bridge y discrepancias

Se revisó el archivo de Descargas SemiApiBridge.h y se verificó que su SHA-256 no cambió. Se respetan rutas, cabeceras y sobre, pero el JSON plano del header no es compatible con la nueva versión: necesita sesión, secuencia, UUID de lectura y sensores estructurados. El contrato incluye tabla de correspondencias y razones; una prueba rechaza ese JSON con 400, sin normalización silenciosa. El header sigue sin compilar/probar y su physical_control=false mantiene bloqueada la consulta de movimiento. No se editó el archivo original.

## Riesgos abiertos y siguiente revisión

- Cotejar/adaptar el bridge por separado con el compañero; no conectar callbacks a motores en este gate.
- HTTP local no cifra tokens; mantener red confiable y sin exposición pública. Autenticación del operador/HTTPS y políticas de múltiples usuarios quedan pendientes.
- Las pruebas no establecen latencia, jitter, retención de logs ni capacidad sostenida de SQLite. Ajustar frecuencia de heartbeat con evidencia; no hay limpieza automática de historia.
- Para reinicio de contadores del ESP32 se exige rotar explícitamente la sesión, no aceptar secuencias antiguas. Ver procedimiento en GATE5B_IMPLEMENTATION.md.
- No usar ADC como humedad calibrada, tensión como porcentaje de carga, ni LiDAR como clasificador de arena. NPK requiere modelo/protocolo y validación agronómica.
- Movimiento físico sigue sujeto a driver, alimentación, circuito de parada, firmware, watchdog monotónico local y validación contenida en una iteración posterior.

No se avanza a otro gate. La preparación de una integración de diagnóstico está terminada dentro de los límites de software permitidos; ninguna prueba física se declara aprobada.

## Archivos nuevos/modificados (sin incluir archivos locales del editor)

- .env.example
- README.md
- backend/apps/agriculture/setup_views.py
- backend/config/security.py
- backend/config/settings.py
- backend/config/urls.py
- backend/config/views.py
- docs/API_CONTRACTS.md
- docs/ARCHITECTURE.md
- docs/HARDWARE_STATUS.md
- frontend/package.json
- frontend/playwright.config.ts
- frontend/playwright.operational.config.ts
- frontend/src/Installation.tsx
- frontend/src/Runtime.tsx
- frontend/src/components/ui.tsx
- frontend/src/pages/Control.tsx
- frontend/src/pages/Data.tsx
- frontend/src/pages/Home.tsx
- frontend/src/pages/Status.tsx
- frontend/src/types/api.ts
- backend/adapters/esp32_diagnostic.py
- backend/apps/devices/__init__.py
- backend/apps/devices/authentication.py
- backend/apps/devices/contracts.py
- backend/apps/devices/management/__init__.py
- backend/apps/devices/management/commands/__init__.py
- backend/apps/devices/management/commands/register_device.py
- backend/apps/devices/migrations/0001_initial.py
- backend/apps/devices/migrations/__init__.py
- backend/apps/devices/models.py
- backend/apps/devices/services.py
- backend/apps/devices/tests.py
- backend/apps/devices/views.py
- docs/GATE5A_CONTRACTS.md
- docs/GATE5B_IMPLEMENTATION.md
- docs/GATE5_RESULTS.md
- frontend/e2e/device.spec.ts
- frontend/playwright.device.config.ts
- frontend/src/components/DeviceReadings.tsx

Incluye este informe GATE5_RESULTS.md. Logs locales ignorados: docs/repository-checks/gate5. Capturas de fixtures E2E: docs/evidence-gate5.

Estado final de puertos: no había listeners en 8000/5173 ni en los puertos E2E 8002/5174, 8003/5175 y 8004/5176 al cierre. Las suites cerraron sus servidores temporales; no se inició un servidor de desarrollo permanente.
