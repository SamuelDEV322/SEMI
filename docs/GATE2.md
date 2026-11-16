# Gate 2 — implementación, decisiones y evidencia

## Estado

Se evolucionó el proyecto Gate 1 existente, sin crear otro SEMI. Gate 2A y Gate 2B están implementados dentro de los límites de software autorizados. **No se abrió un puerto físico, no se rotó un A1 y no se accionaron motores.**

La adquisición física USB queda pendiente de validación. El núcleo del supervisor fue compilado y probado de forma nativa, con salidas falsas. El proyecto ESP-IDF no fue compilado para placa ni flasheado: falta SDK/placa confirmados.

## Continuidad y recuperación

Git seguía sin commits, con todos los archivos sin seguimiento. La comparación contra el ZIP entregado de Gate 1 no encontró cambios de código del usuario. No se hicieron commits automáticos.

Antes de modificar archivos se guardaron código y una copia SQLite consistente mediante sqlite3.backup en `outputs/SEMI-checkpoint-before-gate2-20261115-151030/`. La base contenía 15 muestras. Se compararon todos los campos originales después de migrar y después de ejecutar E2E: se conservan sin cambios. No se ejecutó seed_demo ni Playwright sobre demo.sqlite3.

Los archivos y evidencias originales de Gate 1 permanecen disponibles; `docs/evidence/` no se reutiliza para Gate 2. Hay checkpoints ZIP de Gate 2A en outputs. Para recuperar datos, detener los procesos y trabajar desde una copia del respaldo; no revertir migraciones sobre la única base. No se borraron registros históricos.

## 2A: Control y accesibilidad

- Pantalla de operación independiente a 100dvh, con safe areas y salida explícita. La navegación inferior se oculta en Control.
- Conexión esencial, radar, cuatro mandos, velocidad y parada visibles simultáneamente, sin desplazamiento. Probado a 360x640 y 390x844, tablet/escritorio y horizontal 740x360.
- Objetivos direccionales y parada de al menos 44 px. Pulsación mantenida, pointer capture, liberación, cancelación, blur, visibilidad y teclado. Un puntero activo; mandos contradictorios no se combinan.
- Orden activa y estado confirmado por simulador diferenciados. Una solicitud de parada sin ACK se indica sin confirmación. Ningún texto acredita detención física.
- Tema claro por defecto, oscuro y sistema, preferencia local persistente y script anterior al render para evitar destello. Colores semánticos y radar/gráficas adaptados.
- Textos secundarios aumentados en vistas habituales; detalles técnicos en diagnóstico. Comprobación automatizada de contraste del texto secundario sobre superficie >=4,5:1 en ambos temas. Esto no es una certificación completa WCAG.
- Errores de historial, última lectura, puntos y LiDAR se muestran en su dominio. Una falla del historial no aparece en Control. Conectividad del sistema sigue siendo transversal.

Los tamaños, colores y composición conservan la identidad de Gate 1. Se priorizó el control sin scroll sobre reproducir el wireframe fijo. No se modificó Figma ni se afirma una reproducción 1:1.

## 2A: Puntos y mediciones

Nueva entidad SamplingPoint: ID, nombre único, ubicación none/manual_schematic, X/Y opcionales 0–100 y creación. Sample tiene una FK nullable y protegida. Los campos antiguos se mantienen como instantánea histórica compatible con Gate 1.

La migración 0002 agrupa etiquetas exactas no vacías solamente cuando sus posiciones conocidas no se contradicen. Una única ubicación histórica puede definir el punto incluso si hay muestras posteriores sin coordenadas. Si hay posiciones distintas o no válidas, los registros quedan sin asociación, se preservan y la interfaz los señala como pendientes. No se infieren coordenadas geográficas.

La parcela consulta **SamplingPoint.latest_sample**, no la última muestra que casualmente tenga X/Y. Se muestran ID en el esquema y nombre, NPK, fecha y antigüedad en una lista separada para evitar solapamientos. No se interpola espacialmente.

Flujo: Datos -> crear punto -> asignar X/Y opcional -> seleccionar punto -> guardar muestra demo -> consultar historial/gráfica del punto. También se puede ubicar o ajustar un punto existente. Las gráficas filtran ID de punto, variable y periodo; TimeChart rechaza una colección con varios puntos. Null/inválido produce huecos, no cero. La UI consulta al backend las 100 muestras recientes del punto seleccionado (no un recorte global mezclado); el API permite hasta 200 por consulta. Paginación completa sigue pendiente.

### Extensiones API compatibles

- GET/POST `/api/sampling-points/`; GET/PATCH `/api/sampling-points/<id>/`.
- Point: `{id,name,position_method,x,y,created_at,latest_sample}`.
- Sample añade `sampling_point: integer|null`; el resto del contrato se conserva.
- POST `/api/demo/capture/` admite sampling_point. POST de muestras puede usar FK sin etiqueta; el servidor copia el nombre correcto.
- Historial y muestras aceptan `point`, `since`, `until` (fechas ISO con zona) además del límite.
- No existen endpoints de borrado de puntos o muestras.

## Aislamiento E2E

Playwright inicia Django en 8002 y Vite en 5174 con `SEMI_DATABASE=e2e.sqlite3`. No reutiliza servidores existentes. prepare_e2e rechaza cualquier nombre de base distinto de e2e.sqlite3, migra, limpia exclusivamente esa base de pruebas y ejecuta seed_demo. La base de demostración usa 8000/5173 y queda intacta. Las pruebas unitarias usan la base temporal del runner Django.

## 2B: A1 USB opcional

SerialLidarProvider implementa el protocolo estándar clásico de cinco bytes de SLAMTEC. Verifica descriptor, identificación de familia A1 y salud antes de SCAN; usa calidad, bits de sincronía, ángulo Q6 y distancia Q2. No implementa express scan, SLAM, localización ni control de vehículo. Referencias: [SDK oficial](https://github.com/Slamtec/rplidar_sdk), [definiciones de protocolo](https://github.com/Slamtec/rplidar_sdk/blob/master/sdk/include/sl_lidar_cmd.h). La revisión concreta y kit eléctrico siguen pendientes de verificar físicamente.

No hay apertura al importar, construir el adaptador, arrancar Django o elegir una fuente en la UI. El comando `lidar_usb` requiere autorización local, `--mode real`, puerto y revisión explícitos y confirmación interactiva **INICIAR A1**. Abrir el puerto/DTR e iniciar SCAN puede activar el motor de rotación del sensor; se advierte antes de abrirlo. Se permite únicamente un kit A1 compatible con control DTR y modo estándar a 115200; otras revisiones/modos se rechazan o requieren una integración específica.

Lector separado -> último escaneo JSON mediante reemplazo atómico -> Django -> HTTP -> radar. Sin broker ni WebSockets. Archivo acotado a 1 MiB, máximo 4096 puntos. No se guardan todos los puntos en SQLite. Django no mantiene un puerto serie ni ejecuta comandos USB. El archivo es IPC local de un usuario de diagnóstico; no es un canal para productores remotos no confiables. Se admite un único lector por archivo.

POST `/api/lidar/source/` selecciona mock/replay/real. Real requiere SEMI_LIDAR_DIAGNOSTICS=1, pero no inicia el lector. El modo de control continúa siendo demonstration aunque LiDAR sea real: la procedencia de la percepción se muestra por separado. Replay reproduce un fixture **sintético**, no una grabación del A1.

Scan conserva los campos existentes y añade `status`, `age_ms`, `error`, `received_monotonic` (interno entre procesos), fuente y validez. Estados: disconnected, no_data, valid, stale, error; mock conserva simulated/unavailable. Pasados 2000 ms sin escaneo, deja de dibujarse como actual. El navegador también aumenta la antigüedad desde su recepción usando performance.now. Reiniciar el lector limpia el estado; no hay reconexión automática del puerto.

Cierre con Ctrl+C, STOP del propio LiDAR y liberación del handle incluso si se retira el USB. Cambiar fuente de visualización no apaga un lector independiente: cerrarlo en su terminal. El enlace inalámbrico deseado conserva el contrato Scan como futura integración UART–Wi-Fi; no se implementó firmware de puente.

### Ejecutar la demostración (PowerShell desde SEMI)

```powershell
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
# Otra terminal:
npm.cmd --prefix frontend run dev
```

Abrir http://127.0.0.1:5173. En esta sesión había una instancia anterior en los puertos habituales; la instancia Gate 2 verificada se dejó en http://127.0.0.1:5175 con backend 8010. Para reproducir esa variante: usar runserver 127.0.0.1:8010 y DJANGO_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5175; en la terminal frontend, VITE_BACKEND_TARGET=http://127.0.0.1:8010 y npm run dev -- --port 5175. No volver a cargar seed para conservar las horas actuales; seed_demo sigue siendo idempotente si se quiere actualizar exclusivamente las 12 muestras identificadas del seed.

### Diagnóstico USB futuro — no ejecutado durante Gate 2

Instalar opcionalmente `backend/requirements-lidar.txt`. Tras revisar y autorizar alimentación, revisión y kit, configurar SEMI_LIDAR_DIAGNOSTICS=1 en el entorno de Django y del lector, reiniciar Django y seleccionar Sensor USB en Estado. En otra terminal, con el puerto confirmado por el equipo:

```powershell
$env:SEMI_LIDAR_DIAGNOSTICS="1"
.\.venv\Scripts\python.exe backend\manage.py lidar_usb --mode real --port PUERTO_CONFIRMADO --revision REVISION_CONFIRMADA
```

El comando pregunta antes de abrir el puerto. No proporcionar confirmación sin validación del equipo. Archivo por defecto backend/runtime/lidar-latest.json; SEMI_LIDAR_SPOOL puede cambiarlo y debe coincidir en ambos procesos. No se hicieron mediciones de rendimiento del A1 real. La alineación física entre sensor y frente del robot tampoco se verificó: la fuente USB usa referencia del sensor (mounting_unverified), no una orientación del chasis calibrada.

## 2B: Supervisor temporal independiente

`firmware/safety/supervisor.hpp`: núcleo C++ portable con MotorOutput abstracto; arranque STOP, armado autorizado, nonce de arranque, sesión exclusiva, época, secuencia, límites y plazo monotónico. STOP/caducidad desarman; fault enclava; reinicio y cambio de nonce invalidan mensajes antiguos. El transporte futuro debe autenticar origen/sesión antes de pasar authorized=true; el booleano del ensayo no es autenticación criptográfica.

`firmware/esp32_fake`: proyecto ESP-IDF preparatorio sin GPIO, PWM ni driver. Usa esp_timer_get_time y callback periódico local de 10 ms, separado de HTTP. La salida es exclusivamente FakeOutput y no se acepta movimiento por red. [Temporizador Espressif](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/api-reference/system/esp_timer.html).

150 ms de renovación / 450 ms de vigencia y 10 ms de supervisión son **candidatos de ensayo**, no valores de seguridad aprobados. Permiten ensayar ausencia de renovaciones y margen ante pérdidas. Las pruebas deterministas barren pasos de reloj de 1–10 ms; observaron retraso máximo de 6 ms al vencer. No dependen de sleeps del CI, del reloj calendario, de Django o de nuevas órdenes HTTP. No son mediciones de jitter de red ni de ejecución en ESP32. El simulador Django de Gate 1 permanece como simulación de interfaz; no se confunde con este núcleo independiente.

El tiempo real debe comprobarse en la placa con carga, latencia/jitter del enlace, velocidad y distancia de frenado/retención en pendiente. Un callback de software puede retrasarse si se bloquea el microcontrolador. Hace falta watchdog de sistema y protección física de habilitación/parada independiente; no hay certificación ni parada física probada. Pines, driver, corrientes, batería/reguladores y comportamiento mecánico siguen bloqueando motores.

### Pruebas reproducibles

```powershell
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar --verbosity 2
npm.cmd --prefix frontend run build
npm.cmd --prefix frontend run test:e2e
# Compilación opcional de núcleo en Windows (sin ESP-IDF ni hardware):
.\.venv\Scripts\python.exe -m pip install -r firmware\requirements-test.txt
.\.venv\Scripts\python.exe -m ziglang c++ -target x86_64-windows-gnu -std=c++17 -Wall -Wextra firmware\safety\test_supervisor.cpp -o firmware\build\test_supervisor.exe
.\firmware\build\test_supervisor.exe
```

Crear firmware/build si no existe. El proyecto ESP-IDF requiere instalar SDK compatible y seleccionar placa posteriormente; **no fue compilado ni flasheado** en este gate.

## Resultados y errores conocidos

- 34 pruebas backend aprobadas, incluyendo migración desde 0001, preservación, asociación ambigua, FK, posiciones y filtros; parser/descriptor, puerto ausente/ocupado, confirmación, mock/replay, obsolescencia, fallo y cierre.
- 18 pruebas Chromium aprobadas: 360/390/768/1440, horizontal, claro/oscuro, tema persistente/sistema, contraste de tokens, NPK, aislamiento de errores, mouse/teclado/táctil/cancelación/visibilidad/foco/desconexión y ausencia/obsolescencia/error.
- TypeScript/Vite y Django check correctos, migraciones sin cambios pendientes. C++ nativo compilado y ejecutado con fake.
- Logs y capturas: docs/evidence-gate2. Gate 1: docs/evidence, conservado.
- Corregidos durante desarrollo: prueba heredada dependiente del cwd; distinct de migración con ordenación implícita; codificación de acentos; etiquetas superpuestas; test de contraste que no contemplaba hex de tres dígitos. La migración fallida se revirtió transaccionalmente y los registros se verificaron contra respaldo.
- Limitaciones: pruebas móviles emuladas Chromium, no teléfono físico/Safari; historial UI limitado a 100 recientes; puntos coincidentes pueden compartir marcador, la lista mantiene ambos; sin autenticación de usuarios para despliegue compartido. No exponer públicamente.
- Pendiente físico: A1, kit/revisión/puerto/alimentación, rendimiento y cierre físico de motor LiDAR; compilación/temporización ESP-IDF en placa; toda activación de motores del vehículo.

## Gate 3 recomendado

Validación autorizada de solo lectura del A1: verificar kit/revisión/tensión, seleccionar puerto conscientemente, registrar identificación/salud, tasa/latencia y pérdida USB, comprobar cierre de rotación y antigüedad en interfaz. Después, compilar el proyecto ESP-IDF con fake en la placa confirmada y medir caducidad sin actuadores. No habilitar vehículo ni GPIO hasta revisar el circuito de seguridad y obtener autorización explícita. No se avanzó automáticamente a Gate 3.
