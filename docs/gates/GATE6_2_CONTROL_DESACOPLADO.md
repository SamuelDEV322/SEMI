# SEMI — Gate 6.2: control desacoplado y LiDAR discreto

Fecha: 18 de noviembre de 2026. Repositorio existente `SEMI`, rama `main`, HEAD inicial `f934304`. Árbol limpio antes de comenzar. Cambios locales, sin commit ni push. No se modificó firmware, configuración local de fuentes ni datos históricos. No se abrió ningún puerto COM ni se inició un dispositivo.

## Resultado y límites

Se puede demostrar, sin hardware, el radar y las intenciones de tracción y de cremallera de forma independiente. El perfil operativo conserva las fuentes reales y muestra ambos controles de motores deshabilitados. Una respuesta HTTP únicamente confirma el procesamiento de una intención en el simulador; no demuestra desplazamiento, posición ni parada física.

| Dominio | Implementado | Fuente física |
|---|---|---|
| LiDAR | 120 rayos geométricos repetibles, etiqueta «LiDAR · Simulación», estado y diagnóstico propios | Adaptadores USB/real y replay conservados. No iniciados ni comprobados físicamente en este gate |
| Tracción | Pulsación mantenida, direcciones, baja/media y parada en simulación | Bloqueada; broker ESP32 STOP-only intacto |
| Cremallera | Subir/bajar/soltar, exclusión de opuestos, caducidad e idempotencia en simulación | `BlockedRackProvider`, sin salida de motores ni opción para habilitarla |

No se crearon migraciones, modelos, servicios permanentes ni dependencias. No hay SLAM, detección de materiales, navegación automática, maniobras de reversa ni geofence.

## 1. Auditoría y arquitectura

Antes del cambio, `MockLidarProvider` tomaba el escenario de `MockRobotProvider` y la vista LiDAR comprobaba el error de tracción. Un fallo de ese enlace podía retirar las distancias. No existía un dominio de cremallera en la API. React ya calculaba la disponibilidad de tracción a partir de su estado y no del escaneo; se conserva esa separación.

Ahora:

- `MockLidarProvider` tiene su propio escenario. Simula la intersección de rayos con una habitación rectangular y un círculo, ambos ficticios. Ángulos cada 3°, hasta 120 puntos, unidades mm del contrato sintético, sin relación con dimensiones del robot o la maqueta. No cambia al enviar comandos de motores.
- `MockRackProvider` compone una **instancia distinta** del supervisor lógico `MockRobotProvider`. Reutiliza ventanas, secuencias, exclusión de operadores y caducidad, sin compartir estado con las orugas. El mapeo interno de up/down a intenciones forward/backward es privado del simulador; no envía comandos de tracción ni utiliza sus salidas.
- `registry.demo_domains` conserva estados independientes por simulador del terreno. Un reinicio explícito del simulador los reinicia; cambiar el estado de un dominio no reinicia los otros.
- `BlockedRackProvider` es la única salida fuera del perfil demo y rechaza cualquier orden, incluido un cuerpo que pretenda declararse demo. No existe implementación GPIO/PWM para sustituirlo cambiando una variable.
- `useHeldActuator` comparte únicamente la interacción del navegador. `useManualControl` y `useRackControl` conservan sesiones, secuencias, ventanas, errores y confirmaciones independientes.
- El panel desplegable de diagnóstico agrupa LiDAR, tracción y cremallera por separado. El fallo del escaneo se presenta junto al radar. El error del módulo se presenta en su propio estado.

Los estados demo residen en memoria de **un proceso Django**. Reiniciar empieza en STOP. No son un broker entre múltiples workers ni un supervisor físico. Su caducidad se evalúa mediante reloj monotónico al observar o procesar el estado; no se afirma que exista una tarea autónoma de parada de hardware. El supervisor local de ESP32 de gates anteriores sigue siendo requisito para una integración futura.

## 2. Contratos preparados, sin rutas redundantes

Se conserva la envoltura `schema_version=1.0`, `mode`, `server_time`, `data`, y los contratos anteriores continúan siendo válidos. Los tipos `MotionCommand`, `RackCommand` y `LidarScan` distinguen responsabilidades en Python/TypeScript; `LidarScan` mantiene el contrato previo `Scan`.

| Ruta | Evolución |
|---|---|
| GET `/api/robot/status/` | Añade `rack` con disponibilidad, procedencia, estado, autorización física falsa y ventana propia |
| GET `/api/lidar/latest/` | Fuente demo independiente. La fuente real sigue el recorrido de Gate 6.1. Un error físico nunca provoca fallback mock |
| POST `/api/control/command/` | `domain` opcional: traction por defecto; rack para el módulo; all exclusivamente para STOP general |
| POST `/api/demo/scenario/` | `domain` opcional: traction/rack/lidar/all. Sin campo conserva all por compatibilidad con los ensayos anteriores. Solo demo y herramientas de desarrollo |
| GET `/api/device/commands/next/` | **Sin cambios**. Autenticación y prohibición de movimiento físico conservadas |

### Intención de cremallera

Ejemplo ficticio: los identificadores y la ventana se obtienen del estado de la **demostración actual**; no son credenciales de un ESP32.

```json
{
  "mode": "demonstration",
  "domain": "rack",
  "action": "up",
  "device_id": "demo-default",
  "request_id": "54284748-c8ab-4e68-8e10-2a7b55e27507",
  "session_id": "08d834c6-c264-4338-a726-56325478d006",
  "seq": 1,
  "epoch": 0,
  "window_id": "ventana-obtenida-del-estado-demo",
  "max_duration_ms": 450
}
```

- `action`: up, down o stop; sesión UUID y secuencia creciente por dominio; `request_id` UUID nuevo para cada renovación y reutilizado únicamente al reintentar exactamente la misma petición.
- Duración 1–450 ms para movimiento; STOP admite 0. La duración efectiva se limita también por la ventana válida. La renovación del navegador ocurre cada 150 ms. Son parámetros de simulación, sin garantía de frenado o recorrido físico.
- ACK: `result=accepted_simulated`, `acceptance=accepted|duplicate`, `hardware_acted=false`, `execution_state=unverified`, identificación de solicitud/dispositivo y `rack` actualizado. El estado lógico puede ser stopped_simulated/raising_simulated/lowering_simulated/unavailable/error. Nunca se confirma ejecución física.
- Duplicar el cuerpo y su identificador devuelve el estado actual sin renovar el plazo ni repetir movimiento. Cambiar el contenido del mismo identificador devuelve 409. Se conservan 256 identificadores recientes; al expulsar uno, la secuencia antigua sigue siendo rechazada. El cliente no debe reutilizar IDs antiguos con nuevas secuencias. La memoria de sesiones conserva los límites previos del simulador.
- Un operador diferente no puede renovar la orden del propietario actual. Up/down opuestos requieren STOP previo. Época/ventana vencida o secuencia antigua: 409. Dispositivo demo incorrecto o estructura/duración inválida: 400. Sin CSRF: 403. Enlace del módulo desconectado o error: 503. Movimiento físico: 403.

### Parada general y compatibilidad

El cuerpo anterior de tracción sigue funcionando sin `domain`. Para cancelar ambos dominios se añade `domain=all` a una orden de tracción con `action=stop`, velocidad, sesión y secuencia. No admite una dirección de movimiento. La parada invalida las ventanas de ambas simulaciones bajo orden fijo de bloqueos. Incluso si la secuencia de STOP está repetida, se cancelan ambas intenciones y se responde con el error, sin inventar una confirmación aceptada.

La liberación individual detiene solo su dominio. Una desconexión o error **del LiDAR** no cancela, crea ni autoriza órdenes de motores. Una pérdida del backend cancela las intenciones locales y deja de renovarlas; no se afirma que el STOP haya llegado cuando falla la red. Las protecciones del broker de dispositivos y su autenticación no se sustituyen por esta simulación. CSRF y contexto de terreno siguen activos en las escrituras del navegador.

## 3. Interacción y responsive

Se conserva el contenedor del radar, la identidad SEMI y los temas claro/oscuro/sistema. La animación se limita a una variación suave de opacidad de un grupo SVG cada seis segundos, sin nuevos bucles de puntos. Respeta `prefers-reduced-motion`. No hay reproducción que finja un escaneo USB.

Orden habitual: encabezado y estado, radar, tracción, Módulo agrícola, velocidad, parada general. En horizontal de poca altura se disponen los mandos en columnas para conservar los objetivos táctiles de al menos 44 × 44 px. En 360 × 640 se reduce el espacio del radar; no se ocultan mandos ni parada. Se mantienen textos de simulación y ausencia de actuación física.

Ambos mandos usan pointer capture e identifican cada puntero. Soltar el dedo de la cremallera no libera las orugas mantenidas con otro dedo. Pointer cancel, pérdida de captura/foco, pestaña oculta, offline, salida de pantalla y errores de mando cancelan la intención. Espacio/Enter ofrecen pulsación mantenida. La parada general responde en pointerdown incluso a un dedo adicional, sin esperar un clic sintético del puntero principal. Las respuestas tardías no reactivan una intención cancelada.

### Capturas locales verificadas

Las capturas se generan con la base E2E aislada. Son simulaciones, no evidencia de hardware. Permanecen locales bajo las reglas de evidencias del repositorio y pueden regenerarse con `test:actuators`.

| Tamaño | Claro | Oscuro |
|---|---|---|
| 360 × 640 | [Captura](../evidence-gate6_2/control-360-light.png) | [Captura](../evidence-gate6_2/control-360-dark.png) |
| 390 × 844 | [Captura](../evidence-gate6_2/control-390-light.png) | [Captura](../evidence-gate6_2/control-390-dark.png) |
| 768 × 900 | [Captura](../evidence-gate6_2/control-768-light.png) | [Captura](../evidence-gate6_2/control-768-dark.png) |
| 1440 × 900 | [Captura](../evidence-gate6_2/control-1440-light.png) | [Captura](../evidence-gate6_2/control-1440-dark.png) |
| 740 × 360 horizontal | [Captura](../evidence-gate6_2/control-740-light.png) | [Captura](../evidence-gate6_2/control-740-dark.png) |

[Parada general después de dos mandos táctiles](../evidence-gate6_2/general-stop.png).

## 4. Archivos creados y modificados

| Archivos | Propósito |
|---|---|
| backend/adapters/rack.py (nuevo) | Proveedor de simulación y bloqueo físico, contrato de ACK e idempotencia |
| backend/adapters/mock.py | Geometría LiDAR independiente e identidad de reinicio demo |
| backend/adapters/registry.py | Estados de dominios por simulador/terreno |
| backend/adapters/contracts.py | Tipos de tracción, rack y escaneo, interfaz RackProvider |
| backend/adapters/lidar_sources.py | El wrapper mock consulta el escenario propio del LiDAR |
| backend/apps/robot/serializers.py | Valida dominios y solicitudes de rack, conserva órdenes previas |
| backend/config/views.py | Despacho por dominio en rutas existentes y parada general |
| backend/apps/agriculture/test_gate6_2.py (nuevo) | 13 pruebas de contratos, aislamiento, caducidad e integridad |
| frontend/src/hooks/useHeldActuator.ts (nuevo) | Interacción mantenida compartida con estado independiente por instancia |
| frontend/src/hooks/useRackControl.ts (nuevo) | Transporte de las intenciones de módulo agrícola |
| frontend/src/hooks/useManualControl.ts | Reutiliza interacción y añade STOP general |
| frontend/src/App.tsx | Disponibilidad del servicio separada del enlace de tracción |
| frontend/src/pages/Control.tsx | Controles compactos, estado y diagnósticos separados |
| frontend/src/components/LidarRadar.tsx | Etiqueta de procedencia y animación discreta solo demo |
| frontend/src/types/api.ts; services/api.ts | Tipos y cliente, misma ruta de órdenes |
| frontend/src/styles/gate2.css | Rack, radar discreto y distribución horizontal compacta |
| frontend/e2e/actuators.spec.ts; playwright.actuators.config.ts (nuevos) | 21 pruebas, base aislada y capturas |
| frontend/e2e/gate2.spec.ts | Ajusta etiqueta de simulación esperada, preserva regresión |
| frontend/package.json | Script test:actuators, sin nuevas dependencias |
| README.md; docs/ARCHITECTURE.md; docs/API_CONTRACTS.md | Referencias a esta evolución |
| Este informe | Resultado, contratos, evidencia y límites |

## 5. Verificaciones ejecutadas

| Verificación | Resultado |
|---|---|
| Línea base Django | 109 pruebas, OK |
| Línea base TypeScript/Vite | Compilación OK |
| Django final | 122 pruebas, OK: 109 anteriores + 13 nuevas |
| manage.py check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios de modelos pendientes |
| TypeScript/Vite final | Compilación OK |
| test:actuators | 21 pruebas, OK |
| test:e2e | 29 pruebas de Gates 2/4, OK |
| test:mvp | 11 pruebas del perfil operativo bloqueado, OK |
| test:device | 11 pruebas de diagnóstico/ADC real mediante clientes falsos, OK |
| test:sources | 10 pruebas de estados LiDAR de Gate 6.1, OK |
| Black --check / git diff --check | Formato y diferencias sin incidencias |

Total: **122 pruebas Django y 82 pruebas de navegador**. Ninguna requiere placas. Los tests de caducidad de rack utilizan un reloj monotónico sustituido de forma determinista; no duermen esperando tiempos de CI. Los tests de navegador ejercitan mouse, teclado, touch real de Chromium, dos punteros independientes, cancelación, desconexión de red, reconexión sin reanudar, foco, pestaña oculta y salida. Miden visibilidad, tamaño de botones y ausencia de desbordamiento en cinco tamaños y ambos temas.

Durante la verificación se corrigieron un envío accidental de campos de estado dentro de la ventana de mando, la selección ambigua del tema en los tests y la falta de activación de STOP por un dedo adicional. Las ejecuciones finales anteriores corresponden al código corregido; las ejecuciones fallidas no se presentan como aprobadas.

Los logs se guardan localmente en `docs/repository-checks/gate6_2/`. Los rechazos 400/403/409/503 esperados forman parte de pruebas negativas. Las semillas ejecutadas por los tests pertenecen exclusivamente a sus bases aisladas.

Al cerrar, no quedaron servidores escuchando en los puertos normales 8000/5173 ni en los puertos de pruebas 8002/5174, 8003/5175 y 8004/5176. No se detuvieron procesos ajenos ni se dejaron servidores permanentes.

### Conservación

Se comparó el hash de las filas de **todas** las tablas de `backend/demo.sqlite3` antes y después: idéntico. Se mantienen 17 muestras, 9 puntos, 3 terrenos y 4 sectores; `PRAGMA quick_check=ok`. Sin semillas ni migraciones sobre esa base. No se guardan puntos LiDAR ni estados de rack en SQLite.

También coinciden los hashes de los 13 archivos de firmware fuera de build y de `backend/apps/devices/services.py`. No se alteró el broker STOP-only ni el firmware. `integrity.json` contiene el resumen de esa comprobación local, sin credenciales.

## 6. Cómo reproducir sin hardware

Desde la raíz SEMI, con dependencias ya instaladas:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar apps.devices
npm --prefix frontend run build
npm --prefix frontend run test:actuators
npm --prefix frontend run test:e2e
npm --prefix frontend run test:mvp
npm --prefix frontend run test:device
npm --prefix frontend run test:sources
```

Ejecutar las suites de navegador **secuencialmente**: comparten la base E2E existente. Cada configuración usa sus servidores temporales 8002/5174, 8003/5175 o 8004/5176 y los cierra al finalizar; no reutiliza los servidores normales. Los tests no utilizan `demo.sqlite3`. No ejecutarlos contra una instancia ajena ni cambiar sus puertos a ciegas.

Para una demostración manual, seleccionar explícitamente la configuración al arrancar **la instancia habitual**, sin crear otra simultánea. En la terminal de Django de VS Code, antes de iniciar:

```powershell
$env:SEMI_MODE = 'demonstration'
$env:SEMI_LIDAR_SOURCE = 'mock'
$env:SEMI_DEV_TOOLS = '1'
$env:SEMI_DEVICE_INTEGRATION = 'disabled'
$env:SEMI_LIDAR_DIAGNOSTICS = '0'
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000
```

En la terminal habitual del frontend: `npm --prefix frontend run dev -- --port 5173`. Mantener el proxy existente a 8000. No hay selector de fuente en la UI. Este gate no cambió las variables locales ni dejó una instancia demo normal ejecutándose. Para volver al perfil real, usar la configuración habitual de Gate 6.1 al reiniciar Django. El movimiento permanece bloqueado en ambos perfiles físicos/diagnóstico.

## 7. Referencia documental de hardware, no configuración ejecutable

| Driver | Referencias aportadas por el equipo |
|---|---|
| TB6612FNG | PWMA GPIO2; AIN1 GPIO5; AIN2 GPIO4; STBY GPIO15; PWMB GPIO25; BIN1 GPIO26; BIN2 GPIO27 |
| L298N | IN3 GPIO19; IN4 GPIO21; ENB GPIO18 |
| PWM histórico | 1000 Hz, 8 bits; canales A=0, B=1, cremallera=2 |
| Valores históricos | velocidadRover=150; velocidadCremallera=120. Valores de prueba, sin unidad ni velocidad física calibrada |
| Capacitivo | Referencia del sketch más reciente: GPIO35. Verificar cableado y configuración efectiva de Gate 6 antes de cualquier cambio |

Estas referencias no se copiaron a una configuración de salida ni habilitan pines. No prueban compatibilidad con la batería aproximada de 24 V.

El original `firmware/legacy/Rover_Cafetero_Original.ino` usa `ledcSetup`, `ledcAttachPin` y `ledcWrite` por canal. La [guía oficial Arduino-ESP32 2.x → 3.0](https://docs.espressif.com/projects/arduino-esp32/en/latest/migration_guides/2.x_to_3.0.html#ledc) documenta la retirada de las dos primeras API, su sustitución por `ledcAttach` y el paso de canal a pin en los argumentos afectados. Antes de una integración futura hay que confirmar la versión instalada, placa y asignaciones; no compilar/flashear el original suponiendo compatibilidad. No se modificó ni compiló firmware de la placa durante este gate.

## 8. Condiciones previas a integración física

Pendiente de validación física: alimentación, corriente nominal/de arranque/bloqueo, drivers reales y cableado, GPIO, estado seguro al arrancar, STBY/ENB, comportamiento de frenado y pendientes, parada física independiente y distancia de detención.

La cremallera requiere límites mecánicos/finales de carrera confirmados, protección eléctrica/sobrecorriente, exclusión de direcciones opuestas y supervisión local. No habilitarla por duración estimada ni interpretar el temporizador demo como límite de recorrido.

El futuro ESP32 debe imponer STOP por defecto, watchdog independiente de Django, plazos monotónicos locales, renovación/expiración de órdenes, rechazo de secuencias antiguas, reinicio y reconexión sin reanudar órdenes. Debe probarse la parada con el navegador ausente, con fallo de red y con pérdida de alimentación de actuadores, en área contenida y bajo autorización específica. El LiDAR no garantiza esa parada ni reconoce tierra/arena.

**No realizado:** validación de motores, movimiento, GPIO/PWM/STBY, COM, arranque A1 o flasheo. No se midieron velocidades, desplazamientos, alcance físico ni tiempos reales de frenado. La usabilidad automatizada no sustituye pruebas con agricultores ni teléfonos físicos. El siguiente incremento físico requiere revisión y autorización; este trabajo termina en Gate 6.2.
