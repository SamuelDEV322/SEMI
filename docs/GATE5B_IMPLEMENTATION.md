# Gate 5B — Implementación y ejecución

Revisión: 17 de noviembre de 2026. Ver contrato normativo en [GATE5A_CONTRACTS.md](GATE5A_CONTRACTS.md). No se realizaron commits ni push.

## Qué está implementado

- App devices independiente: autenticación por dispositivo, validación estricta, recepción de telemetría/estado e historial autenticado.
- DeviceTelemetryService con transacciones, secuencias, idempotencia, asociación al cafetal y conservación del JSON aceptado.
- StopCommandBroker persistente y limitado a STOP desautorizado. No hay cola de movimiento ni adaptador de motores.
- Esp32DiagnosticProvider de solo lectura adapta mensajes al contrato web existente. MockRobotProvider y proveedores NPK/telemetría/LiDAR anteriores permanecen intactos.
- Configuración separada disabled/diagnostic; configuración de operación física rechazada.
- React distingue conexión de diagnóstico, ausencia de lecturas, ADC sin calibrar, error y obsolescencia. Conserva temas, navegación y diseño. En diagnóstico los mandos están deshabilitados; el simulador permanece disponible en demonstration.
- Detalles de dispositivo en un desplegable de diagnóstico de conexión. Las credenciales no forman parte de ese objeto ni llegan al navegador.

## Estructura y responsabilidades

| Archivo | Responsabilidad |
|---|---|
| backend/apps/devices/models.py | Registro, época de sesión, contadores y mensajes persistidos |
| backend/apps/devices/contracts.py | Serializadores estrictos del protocolo |
| backend/apps/devices/authentication.py | Cabeceras, credenciales externas y comparación segura |
| backend/apps/devices/services.py | Ingesta transaccional, idempotencia y STOP-only |
| backend/apps/devices/views.py | Gateway HTTP, parser limitado, errores y respuestas no cacheables |
| backend/apps/devices/management/commands/register_device.py | Provisionamiento local y rotación explícita de sesión |
| backend/apps/devices/migrations/0001_initial.py | Dos tablas y restricciones; no modifica tablas agrícolas |
| backend/apps/devices/tests.py | Autenticación, secuencias, datos, fallos, tiempo y concurrencia |
| backend/adapters/esp32_diagnostic.py | Proyección de solo lectura para robot/status |
| backend/apps/agriculture/setup_views.py | Selección del proveedor en contexto del cafetal |
| backend/config/{settings,security,urls,views}.py | Configuración, límite CSRF, rutas y ampliaciones compatibles |
| frontend/src/components/DeviceReadings.tsx | Datos sin calibrar y estado de diagnóstico |
| frontend/src/{types/api.ts,Runtime.tsx,Installation.tsx,components/ui.tsx,pages/Status.tsx,pages/Home.tsx,pages/Control.tsx,pages/Data.tsx} | Extensión aditiva de estados y mensajes |
| frontend/playwright.device.config.ts + e2e/device.spec.ts | Pruebas reales HTTP con cliente sintético y SQLite aislada |
| frontend/playwright.config.ts + playwright.operational.config.ts | Hacen explícito integration=disabled en regresiones previas |
| frontend/package.json | Script test:device; sin dependencias nuevas |
| .env.example, README.md y docs | Configuración pública sin secretos y decisiones trazables |

No se añade una clase DeviceGateway separada porque las vistas ya representan ese límite. No se duplica MockDeviceProvider: los proveedores existentes siguen cubriendo demonstration. No se modificó el firmware, incluidos los archivos del supervisor experimental.

## Persistencia y migración

Device conserva ID, cafetal protegido, habilitación de diagnóstico, firmware conocido, última comunicación, sesión UUID y contadores por canal. Solo mantiene la última correlación/respuesta STOP, evitando crear una fila por cada consulta de órdenes.

DeviceMessage conserva los paquetes de telemetry/status aceptados, valores JSON originales, fechas, identificadores y referencia de lugar protegida. Constraints únicos por dispositivo/canal/message_id y por dispositivo/sesión/canal/seq. La fuente es real por el canal autenticado; no es una afirmación de calibración ni certificación física.

La migración devices.0001_initial depende de agriculture.0007. Solo crea tablas/índices; no borra ni transforma muestras ni puntos. No existe cascada para borrar terrenos/puntos con mensajes asociados. No se ejecutaron semillas sobre la base habitual.

Se verificó toda fila anterior por su ID y contenido: 17 muestras, 9 puntos, 3 cafetales, 4 sectores, 86 eventos y relaciones conservados. integrity_check=ok y foreign_key_check vacío. Los únicos aumentos de filas previas corresponden al registro de la migración y metadatos Django de la app nueva (contenttypes 11→13, permissions 44→52). Las tablas devices locales terminan vacías: no se insertaron pruebas del contrato en los datos del usuario. No se generó otro ZIP ni copia paralela del proyecto ni un nuevo backup SQLite redundante.

Los mensajes diagnósticos de estado también conservan identidad para idempotencia. No se ha implementado retención/borrado automático; estimar crecimiento con la frecuencia real antes de uso prolongado. Evitar enviar heartbeats a la frecuencia de renovación de mandos. Como referencia inicial de diagnóstico puede ensayarse heartbeat cada 5 s, con indicador de pérdida a 15 s; no es un parámetro de frenado validado.

## Instalación y arranque (Windows)

Desde SEMI, con el entorno existente y dependencias instaladas como indica README:

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py check
```

La migración ya se aplicó en este equipo conservando datos. No repetir semillas. No iniciar servidores duplicados si los puertos están en uso.

El modo normal conserva integration=disabled. Para preparar diagnóstico en una terminal privada del backend:

```powershell
$env:SEMI_MODE = 'operational'
$env:SEMI_DEVICE_INTEGRATION = 'diagnostic'
$deviceId = Read-Host 'Identificador estable del dispositivo'
$plotId = Read-Host 'ID del cafetal existente'
.\.venv\Scripts\python.exe backend\manage.py register_device --device-id $deviceId --plot $plotId
```

El comando muestra session_id para incorporarlo a la configuración acordada del firmware; no crea un token ni conecta hardware. No permite cafetales demostrativos ni reasignar silenciosamente un dispositivo a otro cafetal. Para consultar IDs locales, puede utilizarse Django shell y Plot.objects.values('id','name','demo'); no adivinar el ID 1 en una instalación ajena.

Proporcionar un token fuerte al backend y al firmware mediante su configuración privada. Ejemplo de carga sin escribir el secreto en el código ni en el historial del comando:

```powershell
$deviceSecret = Read-Host 'Token privado del dispositivo (mínimo 32 caracteres)' -AsSecureString
$plainDeviceSecret = [System.Net.NetworkCredential]::new('', $deviceSecret).Password
$env:SEMI_DEVICE_TOKENS = @{ $deviceId = $plainDeviceSecret } | ConvertTo-Json -Compress
Remove-Variable plainDeviceSecret
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

El backend conserva el secreto en su entorno de proceso. No ejecutar este comando en la terminal de Vite ni copiar SEMI_DEVICE_TOKENS a VITE_*. Para reinicios habituales puede utilizarse el .env ignorado con permisos locales apropiados; no pegar el secreto en documentación, capturas ni Git.

En otra terminal desde SEMI/frontend:

```powershell
npm.cmd run dev
```

Esto solo prepara recepción. No modifica el firmware ni habilita actuadores. Con 127.0.0.1 solo puede acceder el mismo computador. Cuando el equipo autorice ensayos de **telemetría únicamente** desde un ESP32 por LAN, será necesario enlazar Django a la interfaz local adecuada y añadir la IP/host del computador a DJANGO_ALLOWED_HOSTS, sin usar un comodín ni abrirlo a Internet. El ESP32 enviará datos a la IP del computador, no a su propio 127.0.0.1. No se cambiaron firewall, red ni hosts de este equipo durante la ejecución.

## Sesión y recuperación

El firmware necesita conservar la sesión asignada, generar message_id UUID por paquete y mantener tres secuencias independientes (telemetry/status/poll). Si una petición falla, reintentar el mismo ID/cuerpo; no crear una lectura nueva para cada intento de entrega.

Si la placa reinicia contadores, detener la emisión diagnóstica y ejecutar deliberadamente:

```powershell
.\.venv\Scripts\python.exe backend\manage.py register_device --device-id $deviceId --plot $plotId --reset-session
```

Comunicar la nueva sesión al firmware. No borra lecturas; invalida paquetes antiguos y limpia el estado actual. No se ejecuta automáticamente al arrancar Django. `--disable` revoca la recepción de un dispositivo sin borrar su historia. Rotar el token privado es independiente de rotar la sesión.

## Pruebas reproducibles sin placas

Desde SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar apps.devices --verbosity 2
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
```

Desde frontend, de manera **secuencial**:

```powershell
npm.cmd run build
npm.cmd run test:e2e
npm.cmd run test:mvp
npm.cmd run test:device
```

El runner Django utiliza una base temporal aislada. Las tres suites Chromium comparten exclusivamente e2e.sqlite3 y no deben ejecutarse simultáneamente. Sus preparaciones pueden vaciar **esa** base; prepare_e2e rechaza cualquier otro nombre. Las credenciales de test:device se generan efímeramente en el proceso de pruebas, nunca son secretos del dispositivo real. La fixture entra por las rutas HTTP implementadas, no por valores fijos dispersos en la UI.

Puertos temporales: demo 8002/5174, MVP sin integración 8003/5175, diagnóstico 8004/5176. Se cierran al terminar. No se detuvo ninguna terminal ajena ni se dejaron servidores nuevos permanentes.

## Evidencia y límites

La línea base pasó 60 pruebas Django, compilación y 40 pruebas Chromium antes de editar. El resultado final, después de añadir diagnóstico, se documenta en GATE5_RESULTS.md. Los logs crudos están en docs/repository-checks/gate5 y las capturas en docs/evidence-gate5, ignorados por Git.

Se inspeccionó la ventana existente de VS Code: test_gate3.py tenía cambios sin guardar visibles en el título. No se guardó ni modificó ese archivo; tampoco .django-stub-gen ni el firmware. Las pruebas se ejecutan sobre los archivos guardados en disco y no verifican el contenido no guardado del editor.

**Probado mediante clientes simulados:** autenticación, almacenamiento de ADC/voltios ficticios de fixture, duplicados, asociaciones, errores, sesiones, STOP desautorizado, lectura desde un proceso Django independiente, responsive y regresión demo. Las capturas corresponden a fixtures en la base E2E; no prueban un ESP32 físico.

**Pendiente de validación física:** adaptación del SemiApiBridge.h revisado en Descargas al contrato v1.0, compilación/ejecución del firmware, latencia/jitter en LAN, adquisición ADC del sensor capacitivo, resolución configurada, referencias de alimentación, calibración y repetibilidad. No se abrió USB ni se flashearon placas.

**No implementado:** movimiento de orugas/cremallera, PWM/GPIO, navegación, SLAM, clasificación de tierra/arena con sensores, porcentaje calibrado de humedad, NPK físico o estimación de carga de batería. El supervisor experimental anterior permanece intacto y no sustituye un watchdog ejecutado y validado en el ESP32.

## Próxima integración concreta, sujeta a revisión posterior

1. Entregar al compañero el contrato y la tabla de discrepancias del bridge inspeccionado; cualquier propuesta deberá ir en una copia de trabajo propia del equipo, fuera de esta ejecución.
2. En banco sin actuadores, emitir identificación/heartbeat y ADC adquirido, verificar unidades, fechas, resolución y reconexión; devolver registros del commit probado y del firmware/revisión usados.
3. Comparar humedad contra referencias y documentar la calibración antes de admitir porcentajes; determinar el modelo/protocolo real de NPK.
4. Revisar driver, motores/corrientes, batería/BMS/reguladores, circuito de habilitación, cremallera, parada física y frenado en pendiente.
5. Diseñar el control físico en otro gate: operador exclusivo, autorización explícita, watchdog monotónico local, STOP independiente, latencias y pruebas contenidas. Ninguno puede habilitarse cambiando solamente una variable de este gate.
