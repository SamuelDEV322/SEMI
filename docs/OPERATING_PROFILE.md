# Perfil operativo y entrega para pruebas del RPLidar A1

Revisión: 16 de noviembre de 2026. Evoluciona Gate 4 sin habilitar movimiento físico.

## Qué recibe el equipo

- Interfaz habitual sin selector de fuentes, escenarios, reinicio de demo ni diagnósticos de desarrollo.
- Configuración de origen exclusiva del servidor: `SEMI_MODE=operational`, `SEMI_LIDAR_SOURCE=real`, `SEMI_DEV_TOOLS=0`.
- Radar que consume el lector USB existente del A1. No abre puertos al cargar la aplicación ni al iniciar Django.
- Indicación de falta de conexión, falta de lecturas, error y antigüedad; el último escaneo deja de representarse como actual al superar 2 s. Este umbral es de visualización, no de seguridad de locomoción.
- Vehículo, batería y sonda sin valores ficticios: capacidades no integradas y mandos deshabilitados.
- Registro y consulta del cafetal, sectores y lugares conservados. La 0007 solo amplía la procedencia permitida de muestras. Las filas de prueba permanecen intactas y se filtran del perfil operativo.

Activar el origen real **no demuestra** adquisición física, no implementa el enlace ESP32, no permite conducir orugas y no valida NPK. Falta esa integración concreta, no una opción de interfaz.

## Preparación del equipo del compañero (Windows)

1. Obtener este commit en su clon del mismo repositorio. No copiar la base de otra persona ni reemplazar `.env` existente.
2. Seguir README para Python 3.12, Node 24, entorno virtual, requirements, `npm ci` y migraciones. No necesita Docker ni semillas.
3. Instalar `backend/requirements-lidar.txt` en su entorno virtual. Comprobar la etiqueta exacta del A1, revisión del USB-kit, alimentación compatible y puerto COM. No adivinar conexiones ni tensiones.
4. En `.env` del compañero dejar perfil operativo, LiDAR real y herramientas 0. Los valores locales no se versionan. La variable antigua `SEMI_PROVIDER` ya no selecciona proveedor.
5. Iniciar Django en 127.0.0.1:8000 y Vite en 127.0.0.1:5173 como indica README. Sin lector, Control debe mostrar ausencia de lecturas y los mandos bloqueados.

No se incluye un modo que habilite motores del vehículo mediante una variable. Conservar salidas físicas desconectadas durante la validación del software del sensor.

## Inicio deliberado del lector USB

El siguiente comando es un procedimiento para el compañero, **no se ejecutó contra hardware en esta revisión**. En una tercera terminal, desde SEMI:

```powershell
$env:SEMI_LIDAR_DIAGNOSTICS = '1'
$lidarPort = Read-Host 'Puerto COM comprobado en este equipo'
$lidarRevision = Read-Host 'Revisión A1 comprobada en la etiqueta y kit'
.\.venv\Scripts\python.exe backend\manage.py lidar_usb --mode real --port $lidarPort --revision $lidarRevision
```

El lector solicita escribir `INICIAR A1`. Antes de hacerlo, confirmar que el sensor puede rotar y que su montaje permite la prueba. No hay apertura automática ni selección desde el navegador. Para terminar, Ctrl+C en la terminal del lector; debe cerrar el puerto y publicar desconexión. Si desaparece abruptamente, Django y el navegador caducan el último escaneo, sin inventar uno nuevo.

Django y lector deben ejecutarse en el **mismo computador** y compartir `SEMI_LIDAR_SPOOL` (vacío usa `backend/runtime/lidar-latest.json`). No usar el spool monotónico entre computadores: sus relojes no son intercambiables. Iniciar un solo lector. El spool es transitorio y está ignorado en Git.

El adaptador implementa el protocolo estándar A1 a 115200, identificación de familia, comprobación de salud, SCAN estándar y STOP/cierre del **sensor**. No es SLAM ni control de tracción. La revisión escrita es una declaración del operador, no una identificación automática de toda la revisión/compatibilidad del kit. El handshake comprueba la familia; la compatibilidad eléctrica debe verificarse por separado.

SLAMTEC documenta los modelos y uso del puerto en su [SDK oficial](https://github.com/Slamtec/rplidar_sdk/blob/master/README.md) y el inicio/detención de la rotación en el [ejemplo oficial](https://github.com/Slamtec/rplidar_sdk/blob/master/app/ultra_simple/main.cpp). Nuestra implementación compatible es propia y sus pruebas actuales usan fixtures; no afirmar que fue certificada por SLAMTEC.

## Checklist asíncrono: evidencia que debe devolver el compañero

| Prueba | Resultado esperado | Evidencia a registrar |
|---|---|---|
| Sin lector | Fuente real, sin escaneo y mandos bloqueados | Captura Estado/Control y commit probado |
| Puerto ausente/ocupado | Error claro, sin fallback sintético | Mensaje de terminal; no credenciales |
| Inicio confirmado | Pasa por sin lecturas y luego distancias si el sensor funciona | Revisión, puerto local, hora y capturas |
| Referencia y distancia | Comparar objetos a distancias conocidas sin deducir materiales | Medidas de referencia, error observado y montaje/0° |
| Pausa del lector | Último escaneo pasa a desactualizado | Tiempo y captura; no prueba de frenado |
| Desconexión USB | Sin lectura activa, puerto liberado al terminar | Mensaje y capacidad de volver a iniciar manualmente |
| Ctrl+C | Cierre limpio; no quedan procesos lectores | Resultado y captura posterior |
| Control | Sigue bloqueado; no cambia a conectado por tener LiDAR | Captura y respuesta de estado |

Registrar también sistema operativo, versión de pyserial y kit USB. No publicar archivos completos del entorno ni números de serie personales. No se requiere esperar una sesión conjunta para ejecutar este procedimiento, sujeto a la organización del equipo.

## Contratos y extensión concreta

`GET /api/health/` comunica el perfil y capacidades. El sobre puede usar `mode: operational | demonstration`. `GET /api/robot/status/` devuelve `source: real`, `connection: disconnected`, `state: unavailable`, `control.action: null` mientras falte el enlace del vehículo; no es confirmación física de detención. Batería desconocida es `value: null`.

`GET /api/lidar/latest/` mantiene el contrato común: fuente, estado, fecha, edad, validez y puntos (ángulo, mm, calidad). El consumidor valida estructura, números finitos, rangos, procedencia y relojes; un archivo antiguo de otro arranque no vuelve a ser fresco. `POST /api/lidar/source/` siempre responde 405. No hay ruta para activar dispositivos.

`POST /api/measurements/capture/` es el límite de captura común: en perfil operativo devuelve 503 hasta que exista adquisición NPK validada. No escribe muestras. `POST /api/npk/samples/` no permite inyectar valores reales desde el formulario. Las rutas demo se bloquean con 403 en operación. Los comandos operativos devuelven 503, los pedidos de modo real/demo incompatibles 403. Ninguno realiza I/O de motores.

Para integrar NPK, aportar modelo, protocolo, alimentación, unidad realmente entregada, estados de validez, tiempos de contacto y referencia de calibración. El adaptador implementará `NPKProvider.capture`, identificará procedencia real y fecha de adquisición, y asociará la muestra al punto seleccionado. Nunca cambiar solamente `source` a una muestra sintética. La validación agronómica es independiente de recibir bytes.

Para integrar ESP32, aportar firmware y mensajes existentes, versión, placa, driver, alimentación, pines y estado de habilitación/parada. La siguiente implementación deberá confirmar órdenes aplicadas, arbitrar un solo operador y aplicar STOP/caducidad local en el controlador aunque el computador desaparezca. El supervisor aislado actual no detiene motores. No se ha inventado un transporte para sustituir ese contrato pendiente.

## Desarrollo, pruebas y conservación

Las fuentes mock/replay siguen como herramientas internas de regresión, seleccionadas antes de iniciar Django. En `demonstration` no se muestran filas reales; en `operational` no se muestran filas mock/replay. Ninguna selección cambia la procedencia histórica. Sincronizar datos entre personas es otra tarea: Git no incluye SQLite.

La base habitual se mantiene; `prepare_e2e` solo acepta `e2e.sqlite3`. Ejecutar `test:e2e` y `test:mvp` secuencialmente: comparten esa base aislada y usan puertos temporales distintos. No ejecutar semillas en los datos del usuario. La regresión conserva los ensayos anteriores en un perfil explícito de desarrollo; no forman parte del recorrido del agricultor.

El favicon SVG elimina el recurso faltante observado. El error unsafe-eval de la captura procede de una URL chrome-extension/content.js: debe comprobarse con extensiones deshabilitadas. No se relajó la política del sitio para permitir eval.

## Prioridades después de esta entrega

1. Validar físicamente el lector A1 y documentar montaje, orientación y pérdidas en el entorno real, sin prometer detección de arena.
2. Integrar un único contrato de firmware ESP32 con sesiones, confirmaciones, tiempos monotónicos y estado físico verificable. Primero banco sin actuadores.
3. Completar la cadena eléctrica y parada independiente: driver/corrientes, batería/BMS, regulación, protección y frenado en pendiente.
4. Incorporar la sonda real y comprobar repetibilidad contra una referencia; documentar contacto, unidades y calibración sin umbrales arbitrarios para café.
5. Antes de permitir conducción desde el celular: acceso local autorizado, operador exclusivo, medición de latencia/jitter y distancia de detención. HTTP polling actual del radar no es un lazo de protección de motores.

Estas prioridades distinguen software implementado, capacidad preparada y verificación física pendiente. No se avanza automáticamente a un gate nuevo ni se realiza despliegue público.
