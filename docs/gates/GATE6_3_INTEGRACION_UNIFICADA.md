# SEMI — Gate 6.3: integración unificada

Fecha: 18 de noviembre de 2026. Repositorio SEMI existente, rama main. La línea base incluye los cambios locales de Gate 6.2, todavía sin commit, que se conservaron. No hay una aplicación nueva, migraciones, nuevas dependencias ni cambios al firmware diagnóstico previamente utilizado. Sin commit ni push.

## Evidencia y estado de entrega

| Categoría | Evidencia / alcance |
|---|---|
| Adquisición física externa reportada por el equipo | RoboStudio reconoció A1M8-COM8 y mostró puntos/distancias con Scanning aproximadamente 6.76 Hz / 406 rpm. Esta evidencia fue comunicada por el usuario; no se ejecutó ni verificó RoboStudio durante este gate |
| Código listo | Lector USB explícito, exclusión de publicadores, parser estándar, filtrado de puntos, publicación atómica local, API existente y radar React |
| Verificado sin hardware | Handshake y paquetes sintéticos compatibles con el protocolo, lector → archivo → API; API con fixtures → radar; desconexiones, datos obsoletos, bloqueo de motores y supervisores nativos con salidas falsas |
| Pendiente | Escaneos físicos adquiridos dentro de SEMI, revisión efectiva del A1M8/kit, puerto actual, computador, frecuencia real bajo carga y validación humana autorizada |
| No habilitado | Tracción TB6612FNG, cremallera L298N, GPIO/PWM/STBY/ENB, reconocimiento de materiales, SLAM y conducción automática |

COM8 es evidencia del equipo de la captura, no configuración incorporada al programa. El éxito de RoboStudio no demuestra que Django reciba datos. No se utilizó su frecuencia como valor simulado ni como medición de SEMI.

## Auditoría y arquitectura

Se reutilizan `backend/apps/agriculture/management/commands/lidar_usb.py`, `SerialLidarProvider`, `StandardParser`, `LidarSources`, el diagnóstico de Gate 6.1 y GET `/api/lidar/latest/`. No se creó otro lector o endpoint.

Recorrido soportado: A1M8 → USB elegido explícitamente → lector autorizado → archivo latest-only local publicado mediante replace atómico → Django → envoltura 1.0 → radar React. Solo el lector posee el puerto; Django y React nunca lo abren. Los puntos no se almacenan en SQLite.

La auditoría encontró que el recorrido ya existía, pero el lector conservaba nodos sin distancia/calidad válidas y no tenía una exclusión entre publicadores SEMI sobre el mismo archivo. Ahora:

- Solo se publican nodos del parser con distancia positiva y calidad válida. Los marcadores de revolución se procesan incluso si el nodo es inválido. Una vuelta sin puntos válidos produce no_data, sin reutilizar un escaneo como si fuese nuevo.
- El límite de 4096 nodos cuenta también nodos descartados: un flujo inválido sin cierre no crece indefinidamente ni elude el límite.
- Un bloqueo de archivo del sistema operativo admite un solo publicador por canal/spool y se libera al salir o morir el proceso. No se borra manualmente para forzar otro lector. El archivo .lock puede permanecer inactivo después de salir; su existencia no significa que esté ocupado.
- En Windows el puerto serie requiere posesión exclusiva; en POSIX se solicita también exclusive al adaptador. El bloqueo de publicación no sustituye la exclusividad del puerto frente a RoboStudio u otro programa.
- El lector publica host, transporte local_usb, puerto elegido, revisión declarada, identificación por handshake, fase y heartbeat. Django rechaza un host declarado distinto del local, manteniendo source=real y estado error, sin fallback mock.
- El diagnóstico añade backend_host, reader_host y same_host. Los archivos legacy sin host siguen siendo compatibles pero same_host=null: no prueban ubicación del lector. El nombre de equipo no es una credencial ni un mecanismo de autenticación.

### Ubicación del lector y transporte

**No está confirmado que el computador de RoboStudio sea el del backend.** Este incremento soporta el lector y Django en el mismo equipo y el mismo canal local. No supone acceso remoto al USB ni interpreta una ruta compartida como transporte de red. El guard de host detecta archivos nuevos de otra máquina; los archivos locales legacy sin procedencia deben retirarse de la prueba humana antes de comenzar, sin confundirlos con adquisición actual.

Si el equipo decide separar computadores, la integración queda bloqueada hasta implementar y probar un transporte explícito: envío HTTPS autenticado de frames con ID de dispositivo/lector, sesión, secuencia, timestamp y TTL, token externo al repositorio y comprobación segura, límite de tamaño/frecuencia y rechazo de replay. La edad debe calcularse con recepción monotónica **del backend** más edad de adquisición transmitida; no se comparan relojes monotónicos de máquinas distintas. No se implementó esa ruta de ingestión remota ni se habilitó el envío actual de telemetría Gate 5 para aceptar escaneos fuera de su contrato. No se debe usar un spool de red como sustituto de este transporte.

## Contratos y estados

La envoltura y las rutas de Gate 5/6 se conservan. El contrato de escaneo incluye sensor_id, source, captured_at, age_ms, status, freshness, valid, unit=mm, angle_convention, max_range_mm, points y error. Cada punto conserva angle_deg, distance y quality obtenidos del parser. El rango de dibujo no recorta ni transforma la medición original de la API: React representa solo puntos dentro del alcance mostrado.

`source=real` identifica el adaptador real, no una prueba física aprobada. Los tests usan fixtures bajo ese contrato y se identifican como tales en este informe. El mock geométrico de Gate 6.2 permanece disponible únicamente en demostración; nunca sustituye un fallo real.

| Estado | Evidencia necesaria |
|---|---|
| Configurado | Fuente real elegida al arrancar; no equivale a dispositivo conectado |
| USB detectado | Inventario pasivo coincide con el puerto seleccionado; no basta para identificar el A1 |
| Identificado | Handshake GET_INFO de familia A1 validado por el lector; revisión física pendiente de confirmar |
| Esperando | Lector reciente, identificado, sin revolución válida todavía |
| Escaneando | Frame válido y reciente; radar con etiqueta REAL |
| Interrumpido | Lector cerrado, desconectado o heartbeat interrumpido |
| Obsoleto | Edad superior al límite existente de 2000 ms; no se mantiene como escaneo activo |
| Error | Contrato corrupto, puerto incompatible/ocupado, sensor no saludable, host incorrecto u otro fallo de adquisición |

La UI conserva «LiDAR · Simulación» para mock y usa «REAL · ESCANEO ACTIVO» / «REAL · SIN ESCANEO» para la fuente física. No representa SLAM, mapa persistente, clasificación de suelo ni prevención de colisiones.

### Tracción y cremallera

Siguen siendo dominios independientes de Gate 6.2: contratos MotionCommand/RackCommand, sesiones, secuencias, ventanas, errores y proveedores separados. Un fallo LiDAR no genera comandos y no condiciona la intención de movimiento manual. Una desconexión de tracción no desactiva el módulo demo, y viceversa. Cada dominio conserva sus propias barreras de autorización.

El perfil real muestra «Tracción física no habilitada» y el módulo «No habilitado». Un STOP HTTP no se presenta como parada física confirmada. El broker autenticado `/api/device/commands/next/` permanece STOP-only, byte por byte sin cambios. No hay una variable para entregar movimiento físico. Los controles demo conservan pulsación mantenida, liberación, foco, pestaña oculta, offline, pointer cancel/capture y dos dedos; STOP general cancela ambas intenciones.

Contrato futuro reservado, **no habilitado en el broker**:

- Solicitud: domain, action, device_id, request_id, sesión autorizada, boot_nonce, época, secuencia creciente y duración máxima limitada.
- El transporte autentica al emisor antes de invocar al supervisor. El booleano authenticated del modelo nativo no implementa criptografía.
- No trasladar un until de fecha/hora de Django al microcontrolador. Se requiere concesión local, época vigente y plazo monotónico local acotado; una entrega retrasada o fuera de sesión se rechaza. Antes de hardware falta validar ese enlace completo y la autenticación en placa.
- Estados independientes: accepted (API validó la solicitud), delivered (dispositivo acreditó recepción) y execution=unverified|confirmed|failed. Solo una confirmación física validada permite confirmed. Los ACK actuales de simulación no avanzan esos estados físicos.
- STOP es una operación independiente de la ventana de movimiento; reconectar o reiniciar no autoriza reanudar. El rechazo o incertidumbre nunca habilita motores.

## Preparación de supervisor local

Se añade `firmware/safety/domain_model.hpp`, separado del firmware flasheado. Compone dos instancias del supervisor nativo existente de Gate 2, con **salidas falsas privadas**, sin Arduino, GPIO ni interfaz de driver físico. Empieza desarmado y physical_authorized siempre devuelve false.

El modelo ejercita armado explícito de ensayo, autenticación recibida del transporte, sesión/nonce/época/secuencia, plazo local, tick monotónico independiente de HTTP, STOP por dominio y STOP general. Para rack exige un estado de límites saludable y rechaza cambio de sentido sin parada; perder límites enclava solo rack. El estado de LiDAR no es entrada del supervisor.

El modelo no es firmware de producción, no incluye tarea ESP32 ni watchdog de hardware, y los flags de límites no demuestran que existan finales de carrera. El supervisor existente en `supervisor.hpp` y el firmware diagnóstico original permanecen intactos. Falta integrar y validar temporizador local/tarea/watchdog, entrada autenticada, límites reales, protección y salidas en un gate autorizado posterior.

## Archivos de este incremento

- `backend/adapters/a1.py`: exclusividad POSIX y filtrado/acotación de revoluciones.
- `backend/adapters/lidar_ipc.py` (nuevo): bloqueo de publicador y host local.
- `backend/adapters/lidar_sources.py`: rechazo de spool declarado remoto.
- `backend/adapters/lidar_diagnostics.py`: ubicación de lector/backend y transporte.
- `backend/apps/agriculture/management/commands/lidar_usb.py`: ejecución bajo bloqueo y metadatos del lector.
- `backend/apps/lidar/test_gate6_3.py` (nuevo): recorrido autorizado hasta API, guardas y errores con fixtures.
- `frontend/src/components/LidarRadar.tsx`: fuente REAL explícita.
- `frontend/src/pages/Control.tsx`: bloqueo de cada dominio visible sin insinuar ejecución física.
- `frontend/e2e/sources.spec.ts`: frames activos con fixtures y capturas de radar real por contrato.
- `frontend/e2e/operational.spec.ts`: actualiza etiquetas de fuente y bloqueo esperadas.
- `firmware/safety/domain_model.hpp`, `test_domains.cpp` (nuevos): preparación nativa inerte y pruebas.
- Este informe, README y arquitectura: trazabilidad. Los otros cambios pendientes en Git pertenecían a Gate 6.2 y se conservaron.

## Validación y evidencia

Línea base: **122 tests Django OK** antes de modificar Gate 6.3. Después: **127 tests Django OK**. Los cinco nuevos cubren comando autorizado → publicación → API, bloqueo antes de construir adaptador, exclusión y liberación del lector, rechazo de host remoto sin fallback y vueltas sin puntos válidos.

TypeScript/Vite compila. `manage.py check` sin incidencias y `makemigrations --check --dry-run` sin cambios. Las suites de navegador utilizan SQLite E2E aislada y se ejecutan secuencialmente, con servidores temporales; no acceden a hardware. Resultados finales y logs locales: `docs/repository-checks/gate6_3/`.

| Suite | Resultado |
|---|---|
| Django | 127 OK |
| test:sources | 10 OK; estados y radar REAL con fixtures |
| test:actuators | 21 OK; incluye dos dedos, STOP general, cancelación y fallo de sensor independiente |
| test:mvp | 11 OK |
| test:device | 11 OK |
| test:e2e | 29 OK |
| C++ test_supervisor | PASS; pruebas deterministas previas con salidas falsas |
| C++ test_domains | PASS; independencia, autorización, límites, caducidad sin HTTP, STOP y reinicio |

Total final: **127 tests Django y 82 tests de navegador aprobados**, más dos ejecutables nativos de prueba aprobados. TypeScript/Vite, formato Black y git diff --check sin incidencias. Los servidores temporales cerraron; no quedaron listeners en 8000/5173, 8002/5174, 8003/5175 ni 8004/5176, ni se detuvieron servidores ajenos.

Las pruebas nativas no compilan ni flashean firmware para ESP32. Una primera ejecución de la regresión MVP señaló textos anteriores de conexión donde ahora se muestra el bloqueo de tracción; se actualizaron esas aserciones para comprobar la nueva semántica, sin relajar el requisito de controles deshabilitados. Esa ejecución inicial no se cuenta como aprobada.

### Capturas: fixtures de contrato, SIN HARDWARE

Estas imágenes contienen la etiqueta REAL porque prueban el contrato del adaptador real con datos sintéticos controlados. **No son capturas del A1M8 adquirido físicamente por SEMI.**

| Ancho | Claro | Oscuro |
|---|---|---|
| 360 px | [Fixture](../evidence-gate6_3/real-contract-360-light.png) | [Fixture](../evidence-gate6_3/real-contract-360-dark.png) |
| 390 px | [Fixture](../evidence-gate6_3/real-contract-390-light.png) | [Fixture](../evidence-gate6_3/real-contract-390-dark.png) |
| 768 px | [Fixture](../evidence-gate6_3/real-contract-768-light.png) | [Fixture](../evidence-gate6_3/real-contract-768-dark.png) |
| 1440 px | [Fixture](../evidence-gate6_3/real-contract-1440-light.png) | [Fixture](../evidence-gate6_3/real-contract-1440-dark.png) |

Las capturas y logs siguen la política local de evidencias, ignorados por Git y reproducibles mediante los tests. Cámara y batería permanecen fuera de la UI del MVP. Las pruebas automatizadas no equivalen a pruebas de usabilidad con agricultores o teléfonos físicos.

### SQLite y conservación

Comparación de hashes de todas las filas: sin cambios en `backend/demo.sqlite3`; quick_check=ok. Conserva 17 muestras, 9 puntos, 3 terrenos y 4 sectores. No se ejecutaron semillas sobre esa base. Las pruebas solo siembran bases aisladas. Los 13 archivos previos de firmware y el broker STOP-only coinciden con sus hashes originales; únicamente se añaden los dos archivos nativos de preparación.

## Reproducción sin dispositivos

Desde la raíz SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar apps.devices
npm --prefix frontend run build
npm --prefix frontend run test:sources
npm --prefix frontend run test:actuators
npm --prefix frontend run test:mvp
npm --prefix frontend run test:device
npm --prefix frontend run test:e2e
.\.venv\Scripts\python.exe -m ziglang c++ -target x86_64-windows-gnu -std=c++17 -Wall -Wextra firmware\safety\test_domains.cpp -o firmware\build\test_domains.exe
.\firmware\build\test_domains.exe
```

Zig ya estaba instalado en el entorno de pruebas; no se añadió a dependencias de ejecución ni es requisito del backend. Ejecutar las suites de navegador secuencialmente porque comparten la base E2E existente. No ejecutar `lidar_usb` como parte de estos tests fuera de su fixture.

## Checklist para una prueba física posterior, NO ejecutada

### Solo LiDAR, requiere autorización adicional

- Confirmar equipo donde está conectado el A1M8, revisión de etiqueta/kit, driver compatible y puerto actual mediante identificación humana; no fijar COM8 ni asumir COM1.
- Cerrar/desconectar RoboStudio y cualquier otro propietario del puerto. Un puerto ocupado requiere resolver su propietario, no matar procesos indiscriminadamente ni reintentar aperturas automáticas.
- Ejecutar lector y Django en ese mismo equipo; comprobar mismo `SEMI_LIDAR_SPOOL` local. Confirmar `reader_host=backend_host` y same_host=true. Para otra topología implementar primero el transporte autenticado descrito arriba.
- Configurar explícitamente SEMI_MODE=operational, SEMI_LIDAR_SOURCE=real y SEMI_LIDAR_PORT con el puerto verificado en las terminales correspondientes. La fuente real configurada no inicia adquisición.
- Solo después de autorización, habilitar SEMI_LIDAR_DIAGNOSTICS=1 **en la terminal del lector** y usar `python backend/manage.py lidar_usb --mode real --port <puerto-verificado> --revision <revision-verificada>`. La confirmación INICIAR A1 implica permitir rotación del propio LiDAR. No se ejecutó este comando físicamente durante el gate.
- Comprobar GET_INFO/HEALTH, espera, escaneos, unidades y calidad; luego API y radar, edad sin reiniciar timestamp. Medir rendimiento real antes de cambiar polling o añadir WebSocket.
- Probar cierre Ctrl+C, retiro/reconexión autorizados y archivo obsoleto; confirmar que no aparecen puntos mock ni reinicio automático de escaneo. Liberar el puerto antes de volver a RoboStudio.
- Mantener alimentación de actuadores bloqueada durante toda la prueba LiDAR.

### Motores: aprobación separada y todavía bloqueada

Referencias documentales, no configuración activa: TB6612FNG PWMA=2, AIN1=5, AIN2=4, STBY=15, PWMB=25, BIN1=26, BIN2=27. L298N IN3=19, IN4=21, ENB=18. PWM histórico 1000 Hz/8 bits, 150/255 y 120/255 son valores históricos sin calibración de velocidad.

Antes de proponer habilitación: confirmar placa/core Arduino-ESP32, esquema y GPIO reales, tensiones de batería/reguladores/motores, corriente nominal/arranque/bloqueo, protecciones, masas y estados de arranque. Una batería aproximada de 24 V no autoriza conexión directa a TB6612FNG o ESP32. Estas comprobaciones eléctricas siguen pendientes y no se propone activar salidas.

El original legacy utiliza ledcSetup/ledcAttachPin y ledcWrite por canal; Arduino-ESP32 3.x retiró las dos primeras y cambió APIs a pin. Confirmar versión efectiva antes de adaptar ese original. No se modificó ni se verificó una compilación de placa en este incremento.

Exigir supervisor local con tarea/timer y watchdog independientes de Django, autenticación, concesión local, STOP independiente, exclusión de opuestos, latencia medida, reconexión/reinicio sin reanudar, parada física accesible, pruebas en área contenida y distancia real de detención. Para rack: finales de carrera/protección de recorrido y sobrecorriente, fallo de cableado de límites y bloqueo mecánico; el temporizador no los reemplaza. Ningún estado del radar debe autorizar ni garantizar la parada de actuadores.

## Referencias primarias

- [SDK oficial SLAMTEC: comandos y formato estándar](https://github.com/Slamtec/rplidar_sdk/blob/master/sdk/include/sl_lidar_cmd.h). Se reutilizan SCAN/STOP/GET_INFO/GET_HEALTH y el parser estándar, sin implementar express/SLAM.
- [Migración oficial Arduino-ESP32 2.x → 3.0, LEDC](https://docs.espressif.com/projects/arduino-esp32/en/latest/migration_guides/2.x_to_3.0.html#ledc).

**Cierre:** código y contratos verificables sin dispositivos; adquisición en RoboStudio reportada por el equipo; adquisición física en SEMI y frenado/movimiento físicos pendientes de autorización y validación. No hubo apertura COM, rotación LiDAR, actuación, flasheo, commit ni push.
