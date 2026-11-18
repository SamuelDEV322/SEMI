# SEMI — Gate 6.1: diagnóstico de fuentes reales y limpieza de UX

Fecha: **18 de noviembre de 2026**, America/Bogota. Trabajo local sobre el repositorio existente, rama main, HEAD inicial d43a57a. Sin push ni commits. No se inició hardware, se abrió un puerto COM ni se accionó un motor.

## Resultado principal

La instancia activa de **este computador** no tiene integrada la fuente ESP32: integration=disabled, cero dispositivos registrados y cero mensajes en backend/demo.sqlite3. El LiDAR tampoco está detectado como adaptador USB serie en Windows: solo aparece COM1 de sistema. No hay proceso lidar_usb ni archivo de escaneos. La indicación USB real era una preferencia de fuente, no una prueba de adquisición. Se identificó además un error de UX independiente: useManualControl inicializaba el mensaje de Control como «El vehículo no está conectado» en todo perfil real, incluso con heartbeat reciente. Ese texto fijo se corrigió; ahora se indica que el movimiento físico está bloqueado durante las pruebas, sin afirmar desconexión.

Esto no invalida la comunicación exitosa que reporta el equipo en Gate 6. Esa prueba no está registrada en la instancia/base inspeccionada. Falta contrastar computador, base, configuración y sesión utilizados entonces. No se inventó una reconexión ni se habilitó diagnóstico automáticamente sin conocer el registro y credenciales correspondientes.

Las correcciones hacen explícitas estas causas, separan configuración/USB/lectura, retiran cámara y batería del MVP y conservan los contratos/datos para futuras integraciones.

## Fase A: auditoría antes de cambiar integración

Se revisaron Git, rutas del backend, modelos, proveedores, parser A1, comando de lector, contratos, firmware Gate 6 y cálculos de React. La auditoría se presentó al usuario antes de aplicar las correcciones. Durante el trabajo se guardó además la eliminación del decorador demo de test_gate3.py: se comprobó que causaba dos fallos y dos errores en seis pruebas. El usuario autorizó restaurar únicamente esa configuración si causaba fallos; se restauró y la ejecución final de 109 pruebas pasó. El archivo vuelve a coincidir con HEAD, sin otros cambios. Había un cambio no confirmado del usuario en SemiSoilSensor.h: se conservó byte por byte y no se modificó firmware.

Las inspecciones de Windows fueron **pasivas**: Win32_PnPEntity, Win32_PnPSignedDriver, serial.tools.list_ports y procesos. No se utilizó Serial/open para averiguar si un puerto estaba ocupado. No se instalaron controladores ni se modificaron firewall/red/terminales.

### Evidencia ESP32 / instancia

Observación inicial: 2026-11-18 08:34:44 UTC (03:34:44 en Colombia).

| Evidencia | Hallazgo |
|---|---|
| Django activo | 127.0.0.1:8000, proceso SEMI/backend, PID inicial 8236 |
| Vite activo | 127.0.0.1:5173, proceso SEMI/frontend, PID 27124 |
| GET health, directo y mediante Vite | operational, device_integration=disabled, physical_control=false, lidar_source=real |
| Configuración del proceso Django | Variables SEMI_* relevantes sin override inicial; se utilizan valores por defecto. No se imprimieron secretos |
| Base usada | SEMI/backend/demo.sqlite3 |
| devices_device | 0 registros |
| devices_devicemessage | 0 registros; no heartbeat, ADC, firmware o sesión que se puedan confirmar |
| Terreno principal | Mi terreno, ID 1; los otros dos terrenos son recorridos demo anteriores |
| Base e2e.sqlite3 antes de probar | 1 dispositivo / 25 mensajes de pruebas; no se tomaron como evidencia física ni se copiaron a la base habitual |
| Firmware Gate 6 inspeccionado | Heartbeat cada 5 s; telemetría cada 15 s; consulta health cada 15 s; timeout HTTP 1800 ms |
| Plazos backend | Conexión reciente hasta 15 s; telemetría desactualizada después de 60 s |
| Consulta React | Estado del robot cada 500 ms en dashboard/control; asistente conserva su consulta cada 1 s |

El firmware mantiene versión/sesión/message_id/secuencias y campos ADC compatibles con Gate 5. Esos intervalos no explican por sí solos la desconexión actual. La configuración efectiva del ESP32 ya flasheado (incluida NVS) no puede deducirse de los archivos locales ni leerse sin abrir su conexión, acción que no se realizó. No se cambió el firmware para resolver un problema de configuración del backend.

### Conexión, autenticación e historia

- Sin registro no existe un dispositivo al cual asociar lecturas, ni una sesión verificable.
- Registrado sin mensaje no equivale a conectado.
- Heartbeat reciente demuestra comunicación autenticada reciente; no implica que ya haya ADC.
- Telemetría histórica puede conservarse después de perder el enlace; se muestra con su fecha y antigüedad.
- Mensajes de otra sesión no se proyectan como lectura actual.
- El rechazo de credenciales conserva el 401 de Gate 5 y no crea mensajes. No existe un registro persistente de rechazos que permita afirmar qué errores 401 ocurrieron antes de esta auditoría. El nuevo diagnóstico diferencia credencial no configurada, configurada sin comunicación comprobada y mensajes aceptados; **no inventa un fallo de autenticación observado**.
- Un backend inaccesible es un error de comunicación de la aplicación, distinto de un dispositivo registrado que dejó de enviar heartbeat.

No se enviaron peticiones de telemetría ficticia a la instancia habitual para probarla.

### Sensor capacitivo

En demo.sqlite3 no existe ADC recibido que se pueda validar. Por tanto, el estado correcto en esta instancia es **sin lecturas recibidas**, no una afirmación de que la sonda física está desconectada.

Gate 5 conserva el JSON de adquisición y el ADC original por dispositivo/sesión. Se volvió a comprobar mediante fixtures: el número no se recalcula, no se convierte en porcentaje ni se crea una muestra NPK. Los estados de lectura válida, inválida/error, ausente y antigua siguen separados. El cambio de pin del usuario en SemiSoilSensor.h permanece intacto; no se atribuye la falta de registros a ese pin sin una medición física.

### Recorrido LiDAR: diez comprobaciones

| Tramo/pregunta | Evidencia / conclusión |
|---|---|
| 1. Detección Windows | Solo Puerto de comunicaciones (COM1), Status OK, ACPI/PNP0501. Sin CP210/CH340/USB-UART/RPLIDAR detectado en las consultas realizadas |
| 2. Puerto COM del LiDAR | No identificable en esta sesión. COM1 es de sistema y no se asignó al A1 ni al ESP32 |
| 3. Controlador compatible | El único controlador de puerto observado es Microsoft para COM1, firmado. No prueba que exista el driver del kit USB del A1 |
| 4. Adaptador configurado | Fuente real seleccionada; permiso local de inicio de lector deshabilitado. Seleccionar la fuente no abre ni inicia el dispositivo |
| 5. Proceso lector | Ningún proceso Python lidar_usb activo |
| 6. Puerto ocupado | No verificable para el A1 porque no hay puerto identificado. No se abrió COM1 ni se hizo una apertura exclusiva para comprobar ocupación |
| 7. Datos recibidos | No existe backend/runtime/lidar-latest.json |
| 8. Escaneo reciente | Ninguno: puntos=0, valid=false, fecha de adquisición ausente |
| 9. Endpoint | /api/lidar/latest/ directo y por proxy responde source=real, status=disconnected, error técnico Reader not running |
| 10. React | Mostraba SENSOR USB · REAL aunque no hubiera lector/escaneo. Se reemplazó por estado de adquisición y fuente configurada claramente separados |

**Causa acotada:** falta detección USB serie en este computador y falta lector/escaneo. No se puede decidir todavía si el sensor está en otro computador, si hay problema de cable/alimentación/kit o si falta un controlador. No se atribuyó una avería al LiDAR ni un COM concreto sin evidencia.

SLAMTEC documenta el kit CP2102/driver CP210x en su [manual A1M8](https://bucket.download.slamtec.com/269e60a69933dffb1067a2ee3405f2918168064a/LM108_SLAMTEC_rplidarkit_usermanual_A1M8_v2.1_en.pdf). La referencia debe contrastarse con la revisión del kit físico; compartir un VID/PID de puente serie tampoco identifica por sí solo cuál aparato es el LiDAR. El [SDK oficial](https://github.com/Slamtec/rplidar_sdk/blob/master/README.md) documenta la rotación por control DTR para A1. Por eso no se abrió el puerto para diagnosticar ni se ejecutó el lector sin autorización.

## Fases B/C: correcciones localizadas

### UX

- Retirados de Inicio y Estado la carga estimada, porcentaje, tensión y avisos de ausencia de batería. Retirada la fila de cámara. Los datos/contratos backend y tipos existentes se conservan para el futuro; no se borran medidas históricas.
- El panel de diagnóstico de suelo tampoco muestra ni vuelca la batería del payload. Sigue mostrando exclusivamente ADC sin calibrar, fecha y fuente de diagnóstico.
- Inicio, conexión, control y Estado comparten el texto derivado de la razón informada por Django. Se eliminó el mensaje fijo de desconexión del hook de control y se prueba que no reaparece con un dispositivo de diagnóstico comunicado. integration_disabled se presenta como **Conexión del vehículo sin configurar**, no como una supuesta avería de radio/sensor.
- Se distinguen vehículo sin registrar, registrado esperando mensajes, sesión esperando comunicación, configuración incompleta y enlace perdido. Los errores de la API siguen separados.
- El sensor capacitivo sin datos dice **Sin lecturas recibidas del sensor de suelo**. Una lectura histórica no convierte automáticamente el enlace en activo.
- La fuente USB se indica como configuración. El radar no se dibuja sin distancias válidas recientes; sigue sin ser un mapa ni un clasificador de materiales.
- Los detalles de adquisición y configuración no secreta están en un desplegable cerrado de diagnóstico; no hay selector de fuente ni botón de inicio físico.

### Backend / adquisición

`GET /api/robot/status/` agrega diagnostics (integration, registered, credential_configured, authentication, reason, edades de heartbeat/telemetría). No contiene tokens ni consulta puertos. Las rutas de telemetría/status y sus reglas de autenticación, sesión e idempotencia no cambian.

`GET /api/lidar/latest/` conserva Scan y añade acquisition. El inventario pasivo de puertos se consulta con una caché de 2 s; si no puede enumerarse, informa unknown en lugar de inventar detección. No es un broker ni conserva estado de seguridad en memoria.

`SEMI_LIDAR_PORT` es una referencia **opcional y pasiva** para diagnóstico, fijada en configuración del servidor. No abre un puerto. Vacía, se utiliza el puerto declarado por el lector autorizado cuando exista; no se selecciona automáticamente el primer USB ni COM1. Si un puerto USB no está identificado, la UI lo dice. Si el puerto configurado discrepa del lector, el escaneo deja de ser válido.

El comando existente `lidar_usb` conserva sus dos requisitos previos de inicio: permiso local y confirmación explícita. Una vez autorizado, publica metadatos de puerto/revisión, fase, identificación A1 comprobada por su handshake y heartbeat local junto al último escaneo. El cierre/error queda reflejado en el archivo. Django sigue sin poseer un handle serie.

Los estados añadidos son not_detected, usb_unidentified, usb_detected, waiting, active, interrupted, stale, error y unknown. **usb_detected representa el adaptador enumerado en el puerto señalado, no identificación automática del A1**. waiting exige identificación por el lector y actividad reciente. active exige puntos válidos recientes. Un heartbeat del lector perdido o un cierre produce interrupción; un escaneo que envejece aunque el lector siga activo produce obsolescencia.

Control y Estado comparten la caducidad visual basada en edad informada + performance.now; aun si falta una respuesta nueva, no conservan indefinidamente un escaneo como actual. Se preserva compatibilidad con escaneos del lector anterior que no incluyen los metadatos nuevos; siguen sujetos a la validación y caducidad existentes.

No se modificaron endpoints ni firmware para movimiento. physical_control y physical_motion permanecen false y los mandos reales siguen deshabilitados.

## Fase D: validación

| Comprobación ejecutada | Resultado |
|---|---|
| Línea base Django antes de editar | 92 pruebas aprobadas |
| Línea base TypeScript/Vite | Compila |
| Django final (agriculture, lidar, devices) | 109 pruebas aprobadas |
| Playwright MVP operativo | 11 aprobadas |
| Playwright fuentes/estados Gate 6.1 | 10 aprobadas |
| Playwright dispositivo diagnóstico | 11 aprobadas |
| Playwright regresión demo Gates 2/4 | 29 aprobadas |
| TypeScript/Vite final | Compila |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes; no se crean migraciones |
| git diff --check | Correcto |
| Integridad SQLite / claves foráneas | ok / sin errores |
| Comparación de todas las tablas habituales | Contenido íntegramente idéntico al inicio |
| SHA-256 del firmware ya modificado por el usuario | Idéntico al inicio |

Los nuevos tests verifican configuración/registro/sesión/credenciales sin filtrarlas, heartbeat sin ADC, telemetría antigua, falta de USB, COM de sistema, puente USB no identificado, puerto seleccionado sin apertura, espera/escaneo/cierre/error y caducidad. También comprueban que el comando no construye el lector sin permiso y confirmación.

Navegador: 360, 390, 768 y 1440 px en claro/oscuro, sin desbordamiento horizontal. La regresión conserva controles compactos, teclado/táctil, cancelaciones y STOP simulado. Se añadió separación y ajuste de texto en la línea de estado de Control para que la explicación de configuración no quede pegada al aviso de bloqueo. La suite nueva recorre los estados de fuente y verifica que no aparezcan cámara/batería, incluidos Inicio/Estado/Control.

**Evidencia simulada:** todos los ADC/escaneos/puertos de fixtures y las capturas de las suites E2E. No se presentaron como ensayos físicos. Se usa e2e.sqlite3 y las bases temporales de Django; nunca se sembró ni vació demo.sqlite3. Ejecutar suites secuencialmente porque comparten la base E2E.

**Evidencia física/pasiva:** la enumeración de Windows, procesos locales y ausencia de puerto USB/archivo de escaneos descritas arriba. No equivale a una prueba de adquisición ni de motores.

No se sustituyó SQLite, no se borró historia y no hubo migraciones destructivas. Continúan 17 muestras, 9 lugares, 3 terrenos, 4 sectores y 86 eventos; devices_device y devices_devicemessage habituales permanecen en cero. El dispositivo y los mensajes existentes en e2e.sqlite3 pertenecen a pruebas aisladas.

Al finalizar permanecen los servidores habituales 8000 y 5173. Django recargó los archivos mediante su mecanismo de desarrollo (cambió su PID); no se detuvo ni duplicó manualmente esa instancia. Los servidores de test se cerraron. No se hicieron commits ni push.

### Reproducir las pruebas

Desde SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar apps.devices --verbosity 2
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
```

Desde frontend, **uno después del otro**:

```powershell
npm.cmd run build
npm.cmd run test:mvp
npm.cmd run test:sources
npm.cmd run test:device
npm.cmd run test:e2e
```

También se comprobó la interfaz **activa** de este equipo a 390 px, claro/oscuro y Control, sin enviar ninguna petición de escritura y sin errores HTTP. Las capturas live-* muestran el estado real sin integración/USB detectados; no son evidencia de un sensor funcionando.

Logs locales ignorados: docs/repository-checks/gate6_1. Capturas de fixtures: docs/evidence-gate6_1. No contienen tokens de dispositivos reales ni forman parte de una prueba física.

## Pendientes: validación física concreta

### ESP32 / sensor capacitivo

1. Identificar el computador y la base usados en la prueba exitosa de Gate 6. Comparar /api/health/, el cafetal seleccionado, registro del ID real y la sesión vigente. No copiar e2e.sqlite3 ni asumir que el historial de otra instancia está disponible aquí.
2. En la terminal **del backend correcto**, revisar la configuración privada y habilitar solo SEMI_DEVICE_INTEGRATION=diagnostic cuando corresponda al ensayo. No se cambia SEMI_MODE ni se habilita movimiento. No se realizaron esos cambios automáticamente.
3. Conservar el registro/credencial/sesión ya utilizados. Si esta es una instalación nueva, realizar el registro explícito documentado en GATE5B_IMPLEMENTATION.md y configurar la misma sesión en el procedimiento Gate 6. No resetear sesiones, contadores o datos a ciegas.
4. Verificar respuesta de /api/device/status/ y /api/device/telemetry/ usando el firmware. Un 401 indica rechazo de autenticación; un 409 puede indicar sesión/secuencia; conservar código/fecha sin imprimir tokens ni Wi-Fi.
5. Confirmar heartbeat reciente (no solo /health/ accesible), ADC original en la sesión correcta y edad/estado en /robot/status/. Tras cortar comunicación deben vencer conexión y lectura por separado; al reconectar no se habilita movimiento.
6. Comparar el ADC con la adquisición real del firmware y confirmar conexión/pin/resolución en banco antes de discutir calibración. No convertirlo en porcentaje ni crear NPK sin dispositivo validado.

### LiDAR / USB

1. Confirmar en cuál computador está conectado el A1. El lector y el archivo de último escaneo deben estar en el mismo equipo que consume Django; el navegador no transmite un USB conectado a otro computador.
2. Con el motor sin iniciar, revisar Administrador de dispositivos/Get-CimInstance y etiqueta del kit. Identificar el puerto del A1 por el hardware y su conexión, separado del ESP32. No usar COM1 de sistema. Si no enumera USB, revisar cable, alimentación/kit y driver apropiado con el equipo; todavía no se ha distinguido cuál de estas causas aplica.
3. Si aparece un puerto USB, verificar el controlador correspondiente a **ese** kit/revisión. No instalar un controlador arbitrario ni asumir CP2102 por el nombre ESP32. Comprobar si Arduino Serial Monitor, RoboStudio u otra aplicación lo utiliza; no abrirlo para averiguar ocupación sin autorización.
4. Opcionalmente configurar SEMI_LIDAR_PORT en la configuración privada de Django, solo después de identificarlo. Un adaptador detectado seguirá sin mostrar escaneo hasta iniciar deliberadamente el lector.
5. **Solo después de una autorización expresa para la rotación del sensor**, usar otra terminal existente de VS Code, desde SEMI. El siguiente procedimiento se documenta; **no se ejecutó en esta revisión**:

```powershell
$env:SEMI_LIDAR_DIAGNOSTICS = '1'
$lidarPort = Read-Host 'Puerto del A1 ya identificado; no el del ESP32'
$lidarRevision = Read-Host 'Revisión comprobada del A1 y kit'
.\.venv\Scripts\python.exe backend\manage.py lidar_usb --mode real --port $lidarPort --revision $lidarRevision
```

El lector exige además escribir INICIAR A1. No ofrecer esta confirmación si todavía no se ha autorizado la rotación. No conecta motores de tracción, GPIO, PWM o cremallera.

6. Verificar secuencia adaptador detectado → sensor identificado esperando datos → escaneo activo; comparar fecha, edad y puntos en /api/lidar/latest/ y React. Si la identificación/lectura falla, conservar el error sin sustituirlo por mock. Cerrar con Ctrl+C y verificar interrupción/sin datos recientes. No abrir dos lectores sobre el mismo puerto.
7. Si el lector está en otro equipo, no compartir sin más el spool monotónico entre computadores. Una futura integración remota requeriría un transporte explícito; no se implementó en este gate.

Estos ensayos quedan pendientes. No se afirma que el ESP32 esté conectado actualmente, que el A1 haya escaneado ni que un STOP web sea una parada física validada.

## Archivos modificados/creados

- .env.example
- backend/adapters/lidar_sources.py
- backend/apps/agriculture/management/commands/lidar_usb.py
- backend/config/views.py
- frontend/e2e/device.spec.ts
- frontend/e2e/operational.spec.ts
- frontend/package.json
- frontend/src/components/DeviceReadings.tsx
- frontend/src/components/LidarRadar.tsx
- frontend/src/components/ui.tsx
- frontend/src/hooks/useManualControl.ts
- frontend/src/pages/Control.tsx
- frontend/src/pages/Home.tsx
- frontend/src/pages/Status.tsx
- frontend/src/styles/gate2.css
- frontend/src/types/api.ts
- backend/adapters/lidar_diagnostics.py
- backend/apps/devices/diagnostics.py
- backend/apps/devices/test_diagnostics.py
- backend/apps/lidar/test_diagnostics.py
- docs/gates/GATE6_1_DIAGNOSTICO.md
- frontend/e2e/sources.spec.ts
- frontend/playwright.sources.config.ts
- frontend/src/hooks/useScanFreshness.ts
- frontend/src/services/sourceStatus.ts

Este informe se añade en docs/gates/GATE6_1_DIAGNOSTICO.md. El único diff previo de firmware (SemiSoilSensor.h) no forma parte de nuestras modificaciones y permanece intacto. Los modelos, migraciones, proveedores mock, configuración privada y base habitual se conservaron.
