# SEMI — Gate 4

Entrega del 15 de noviembre de 2026. Implementación sobre SEMI existente, con Django/DRF/SQLite y React/TypeScript/Vite/Tailwind. No se añadieron dependencias de ejecución, otro workspace, servicios en nube ni dispositivos físicos.

## Resultado y corrección de concepto

El cafetal, sus sectores opcionales y sus lugares de medición son conceptos distintos. Un sector ahora es solo un nombre para organizar el cafetal. Las categorías de material desaparecieron de la API y los formularios agrícolas nuevos; no hay un selector de tierra/arena/otros materiales. El cultivo sigue fijado a café arábica, `Coffea arabica L.`.

La prueba de superficies se trasladó a un subsistema de ensayo. Sus entradas son simuladas y no proceden de las etiquetas del terreno. Ni los sectores ni los puntos autorizan movimiento físico, representan GPS o restringen la circulación manual.

## Onboarding anterior y actual

| Antes: Gate 3 | Ahora: Gate 4 |
|---|---|
| Siete pasos separados | Cuatro etapas con Volver y progreso persistente |
| Clasificación manual tierra/arena/otra | Solo nombre del cafetal; sectores opcionales por nombre |
| Sectores dibujados como franjas iguales | Tarjetas de sectores, sin geometría inferida |
| Punto con ubicación requerida en el asistente | Punto sin sector ni posición permitido |
| Primera medición en un paso independiente | Medición guiada opcional en la revisión final |
| Ejemplo de tierra y arena dentro del recorrido | Ensayo separado en Demostración y ensayos |
| Consulta con última lectura general arriba | Resultados e historial del lugar seleccionado |

Las cuatro etapas son:

1. **Bienvenido a SEMI**: explicación breve y Comenzar.
2. **Mi cafetal**: nombre, café ya preconfigurado y opción secundaria Organizar mi cafetal por sectores. Se puede continuar sin sectores.
3. **Lugares para medir**: nombre opcional, sector opcional, posición opcional mediante toque/clic o teclado. Los códigos P1/P2 se asignan en el servidor. No se pide escribir coordenadas. Crear puntos de ejemplo solo aparece en un recorrido demo y exige una acción explícita.
4. **Comprobar y comenzar**: resumen, conexión identificada como simulada, disponibilidad de lecturas y primera medición opcional. Ver mis mediciones, Controlar SEMI o Ir al inicio guardan la finalización.

No se generan puntos o mediciones para llenar pantallas vacías. Para crear una lectura hay que elegir un lugar y pedir una medición simulada. Se exige que el simulador esté detenido y conectado. Los valores no se interpretan como adecuados, suficientes o deficientes para el café.

Los borradores se guardan con Guardar o Continuar. El paso guardado se recupera al recargar. Salir por ahora no borra la configuración. Repetir bienvenida crea otro cafetal demo vacío; Volver a mis datos recupera el principal. No es un restablecimiento de fábrica.

## Sectores: política implementada

| Situación | Operación |
|---|---|
| Sector vacío y nunca vinculado | Eliminar con confirmación explícita |
| Sector con lugares o asociaciones conservadas | Borrado rechazado con 409; se ofrece archivar |
| Sector archivado | Fuera de selectores de asignación activos; disponible en consulta histórica |
| Sector agrícola archivado | Puede recuperarse sin perder datos |
| Sector histórico de materiales | Permanece archivado; no se elimina ni se recupera como sector recomendado |
| Lugares que dejan un sector | Se desvinculan con confirmación o al modificar el lugar; conservan mediciones y asociaciones conocidas |

Si se archiva o elimina el sector que estaba filtrado, la consulta vuelve a todos los lugares; no queda un filtro invisible.

La interfaz usa un diálogo nativo con Cancelar y Confirmar, foco inicial en Cancelar y cierre mediante Escape. Renombrar/Modificar lleva el foco al formulario. Nunca se eliminan puntos o muestras en cascada. El servidor comprueba que cada ID de sector/punto pertenece al contexto del cafetal solicitado; los casos de IDs ajenos están probados.

Un sector con referencias históricas no se considera vacío aunque ya no tenga lugares activos. El borrado directo mediante ORM también queda bloqueado por las relaciones protegidas de la historia de asociaciones.

Este control de contexto **no equivale a autenticación multiusuario**. La instalación local sigue siendo de demostración, sin control de cuentas; no debe exponerse públicamente. Cambiar el contexto de cafetal no constituye una barrera de seguridad entre usuarios hostiles. La validación de IDs impide mezclar recursos de distintos cafetales en una misma operación contextual.

## Modelo y migraciones

Se conserva el nombre interno `TerrainZone` y la propiedad API `zones` por compatibilidad. En la interfaz se denominan sectores.

- `TerrainZone`: añade `archived` e `historical_surface`. `category` permanece en SQLite como dato histórico, no editable y vacío para sectores nuevos.
- `SamplingPoint`: mantiene IDs, FK a terreno/sector, códigos, posiciones y muestras; añade una relación de asociaciones conservadas.
- `SectorMembership`: relación protegida entre punto y sector, única por pareja. Conserva asociaciones al desvincular. `recorded_at` es la fecha de registro de esa relación, no una posición ni la fecha agronómica de cada muestra antigua.
- `SurfaceTrial`: estado y política conservadora de un ensayo simulado, asociado a un cafetal demo. No forma parte de los sectores agrícolas.
- `Plot.surface` y `Plot.conservative`: columnas antiguas conservadas para no destruir datos; ya no dirigen el flujo agrícola ni se exponen en la configuración. El estado activo del ensayo usa SurfaceTrial.
- `Sample`: sin migración destructiva ni pérdida de su FK, fecha, unidades, valores, fuente o validez.

Migraciones aplicadas:

- **0005**: añade archivo/historia, asociaciones protegidas y SurfaceTrial; conserva `category`.
- **0006**: traduce el progreso de siete a cuatro etapas; mantiene `completed`. Las etapas antiguas 1→1, 2/3→2, 4→3, 5/6/7→4. Las instalaciones completadas quedan en 4 y no repiten el asistente automáticamente. Copia el estado previo de ensayo a SurfaceTrial solo para demos y conserva asociaciones conocidas de puntos a sectores.
- Los valores históricos `sand` y `other` se mantienen literalmente, con `archived=True` e `historical_surface=True`. Las filas `soil` conservan sus nombres y relaciones, sin presentarse como una nueva clasificación de suelo. Pueden renombrarse como sectores descriptivos; no se dibujan sus límites.

La migración se probó primero contra una SQLite de ensayo creada desde el checkpoint. Después se aplicó sobre la base existente, sin ejecutar semillas.

## Estado de SQLite y preservación

Antes y después: **16 muestras, 8 puntos, 3 terrenos y 3 zonas**. Todos los registros originales y sus campos anteriores se compararon fila por fila contra el checkpoint. La única transformación de un campo previo es el mapeo documentado de `Plot.step`. Los IDs, nombres, categorías anteriores, posiciones, valores, unidades, fechas y referencias de las muestras se conservan. `PRAGMA integrity_check = ok`.

La antigua zona `sand` sigue guardada y archivada. Dos zonas `soil` conservan sus datos. Dos estados de ensayo demo se incorporaron como entidades separadas. El progreso de los dos terrenos completados queda en 4; el terreno incompleto que estaba en el antiguo paso 3 continúa en la etapa 2.

Evidencia: `gate4-migration.json`, `gate4-data-preservation.json` y `gate4-migrate-main.txt`. Las pruebas de navegador escriben exclusivamente en `backend/e2e.sqlite3`. No se agregaron muestras ni puntos a la base principal durante este gate.

## Arquitectura y API

Se mantiene polling HTTP y el adaptador HTTP existente. No se añadieron WebSockets, colas, servicios externos ni nuevos lectores de hardware.

`Installation.tsx` conserva la coordinación del contexto y la reanudación. Se extrajeron componentes reutilizables: `SectorManager`, `PointEditor`, `RelativeMap` y `TrialTools`. `Data` usa los mismos gestores para administrar después de la instalación. App, Inicio, Control, Estado, tarjetas, lectura de valores, temas y gráficas existentes se conservaron y evolucionaron.

`GET /api/setup/` mantiene el sobre `schema_version=1.0, mode=demonstration`. La configuración ahora contiene `step` 1–4, `zones` con `id/name/archived/historical_surface/point_count/has_history` y puntos con su última muestra. **Se retiraron `category`, `surface` y `conservative` del contrato agrícola.** Los consumidores TypeScript y las pruebas activas se actualizaron.

Acciones de `POST /api/setup/`, protegidas por CSRF y contexto `X-SEMI-Plot`:

| action | Campos | Efecto |
|---|---|---|
| start / demo | ninguno | Configuración principal o nuevo recorrido aislado; demo solo en desarrollo |
| save | name, step | Nombre y etapa 1–4 |
| sector | name, zone opcional | Crear o renombrar por nombre; rechaza `category` |
| sector_delete | zone, confirmed=true | Solo vacío sin referencias; 409 si está usado/histórico |
| sector_archive / sector_restore | zone | Retirar o recuperar sin borrar historia |
| sector_detach | zone, confirmed=true | Desvincular lugares conservando asociaciones y muestras |
| point | point opcional, name opcional, zone opcional, x/y opcionales | Crear o modificar; ambos valores null permiten guardar sin posición |
| capture | point | Muestra sintética asociada a lugar propio, detenido y conectado |
| complete | ninguno | Finalización persistente, etapa 4 |

`zone` se mantiene como alias de la acción `sector`, con la misma semántica de nombre, sin categorías de material. `surface` es un alias de compatibilidad para antiguos clientes de ensayo y delega al subsistema de pruebas; no edita el terreno. La UI nueva no utiliza ese alias.

El contrato de puntos añade `sector_history` (IDs, nombres y archivo). El endpoint compatible de creación de puntos también asigna código. Las coordenadas internas solo representan un esquema relativo; ninguna se interpreta como metros o GPS.

Errores: 400 validación/ID ajeno en modificación; 403 ensayo fuera del contexto autorizado o control físico; 404 recurso/contexto inexistente en lectura; 409 sector con referencias o movimiento bloqueado por ensayo. Las pruebas positivas de onboarding rechazan cualquier API 404. Los 404 de pruebas negativas del backend son intencionados.

## Ensayo separado: Prueba de superficies

En el menú secundario **Demostración y ensayos**, abrir un recorrido demo. La prueba ofrece Condición normal simulada, Arena detectada (simulación), Superficie desconocida, Pérdida de detección y Desactivar ensayo.

`GET/POST /api/demo/surface/` intercambia `{state, conservative, source:'simulation', physical_detection:false}`. Solo admite un cafetal demo en desarrollo. La condición no se lee de un sector ni de la posición esquemática.

- Normal: permite un nuevo mando manual; no inicia movimiento.
- Arena: STOP inmediato del simulador y rechazo de nuevas órdenes de movimiento.
- Desconocida: conserva la política conservadora configurable de simulación.
- Pérdida: STOP, nunca se sustituye por tierra segura.
- No hay reversa, giro, navegación, geofence ni respuesta de actuadores físicos.

La cancelación del mando activo se aplica en el simulador y también se refleja en el frontend. Las pruebas inyectan la condición por la API de ensayo mientras el control mantiene una orden; así verifican que STOP se debe al estado simulado y no a salir de la pantalla. La interfaz de ensayo permanece separada de la conducción compacta.

## Auditoría UX de las pantallas

| Vista | Cambio y comprobación |
|---|---|
| Inicio | Identidad y lecturas existentes; actividad con nombres cotidianos. Si falta estado, no se afirma que el vehículo esté detenido. Conexión y datos siguen identificados como simulados. |
| Control | Conserva radar y mandos visibles sin scroll, pulsación mantenida, soltar, teclado, táctil, foco, cancelación y STOP. Los errores internos se guardan en diagnóstico; no se muestran como mensajes crudos. La parada del ensayo se indica como simulada. |
| Datos | Mi cafetal y filtro opcional; dónde medí; resultados del punto elegido; historial por punto. Puntos sin lectura o sin posición siguen utilizables. Fuente, fecha, validez y antigüedad visibles. Error de carga y ausencia de datos son estados distintos. |
| Estado | Conserva fuentes LiDAR y mantenimiento; elección USB/diagnóstico y detalles de driver/protocolo dentro de Diagnóstico técnico. La batería principal se describe como no supervisada físicamente. |
| Asistente | Cuatro etapas, sectores opcionales, ninguna selección de materiales, ubicación opcional, botones grandes, Volver, guardado/reanudación y medición opcional fácil de encontrar. |

Las variables ambientales no confirmadas permanecen identificadas en Estado/diagnóstico; se retiró su tarjeta de lecturas vacías de Datos para centrar la consulta en el suelo. Se retiró la etiqueta interna del gate de la pantalla normal.

El esquema es neutro: solo posiciones elegidas, sin franjas, áreas de sectores, límites inventados ni rutas. Los sectores son tarjetas/etiquetas. Se muestra **Esquema orientativo. No representa distancias reales**. En el ejemplo de prueba P1 se guarda sin posición; P2 solo aparece en el esquema tras marcarlo explícitamente con teclado.

Se revisaron claro y oscuro visualmente, foco, contraste semántico existente, etiquetas, diálogos y tamaño de objetivos. El asistente usa 17 px de base y botones >=48 px; el control mantiene objetivos >=44 px. Se mejoraron títulos, textos de registros y placeholders. Las gráficas cuentan con etiquetas y registros textuales para consultar los valores sin depender del trazo o del color.

## Pruebas ejecutadas

- **49 pruebas Django aprobadas**, agricultura y LiDAR, con base de test en memoria. Incluyen las pruebas previas y nueve pruebas nuevas de sectores/puntos/ensayos: posición/sector opcionales, borrar vacío con confirmación, archivar y desvincular sin perder muestras, referencias ORM protegidas, IDs ajenos, categorías fuera del API agrícola, ensayo separado, registros históricos y códigos del API compatible.
- **29 pruebas Chromium aprobadas**: 18 de regresión adaptadas a los controles actuales y 11 de Gate 4. Ocho recorridos completos (360, 390, 768 y 1440 px × claro/oscuro), dos ensayos con mando activo y una prueba de errores/reanudación.
- Primera instalación real de navegador con SQLite E2E vacía mediante `prepare_e2e --empty`; el comando rechaza bases cuyo nombre no sea `e2e.sqlite3`. Las restantes repeticiones crean escenarios aislados mediante la API real. No se falsearon respuestas para simular un onboarding exitoso. Solo la prueba de fallos inyecta deliberadamente 503.
- Flujo probado: omitir sectores, P1 sin posición, P2 con posición elegida, lectura en P1, P2 vacío, gráfica, crear sector posteriormente, asociar P1, renombrar, cancelar eliminación, eliminar sector vacío, archivar sector usado, desvincular y conservar la muestra, recargar y repetir recorrido sin perder el anterior.
- API de ensayo con arena y pérdida durante movimiento lógico: STOP y cancelación del mando. Retorno a normal no inicia movimiento. Ningún comando de UI utiliza modo físico; intento explícito de hardware devuelve 403.
- Regresión de control en 360×640, 390×844, 768×900, 1440×900 y horizontal 740×360. Sin desbordamiento horizontal; radar y mandos simultáneamente visibles y STOP accesible.
- Tema persistente/sistema y contraste de los tokens de texto existentes >=4.5 en las pruebas heredadas. Revisión visual adicional de tarjetas y diálogos claros/oscuros. No es una certificación integral de accesibilidad.
- Django check sin incidencias, migraciones 0001–0006 aplicadas, sin migraciones pendientes. TypeScript/Vite compiló correctamente.
- Supervisor C++ fake heredado ejecutado y aprobado. Sus 6 ms de retraso máximo pertenecen a una prueba determinista, no al ESP32 o a motores físicos.
- Smoke final: ocho lecturas HTTP 200 en 8000/5173, proxy correcto, API agrícola sin campos de clasificación. Solo esos dos puertos de desarrollo quedaron escuchando; los temporales 8002/5174 cerraron.

La primera pasada de navegador detectó una etiqueta de selector insuficiente para el localizador accesible exacto. Se añadió la etiqueta explícita, se corrigió el foco de edición y se repitió la suite completa con éxito. No se ocultaron fallos ni se sustituyeron lecturas del backend para aprobarla.

Evidencias: `gate4-backend.txt`, `gate4-browser.txt`, `gate4-build.txt`, `gate4-checks.txt`, `gate4-supervisor.txt`, `gate4-final-smoke.json`, `gate4-processes.json`, `evidence-gate4` y `evidence-gate4-regression`. Se mantuvo el spec antiguo de siete pasos como documento histórico; la suite activa usa Gate 2 adaptado y Gate 4, junto con las pruebas API heredadas del Gate 3.

## Continuidad, ejecución y respaldo

El código inicial coincidía con la entrega del Gate 3; sí había datos nuevos del usuario respecto a aquella entrega. Se preservaron. Git ya existía y la base estaba sin seguimiento; no se hicieron commits ni cambios destructivos. No había un canal de herramientas para inspeccionar los búferes sin guardar de VS Code; el checkpoint representa los archivos en disco.

Checkpoint previo: `outputs/SEMI-checkpoint-before-gate4-20261115-170614/source.zip` y `demo.sqlite3`, antes de migrar. Entrega: fuentes y evidencias en `outputs/SEMI-Gate4.zip`; copia SQLite consistente separada en `outputs/SEMI-checkpoint-gate4-final/demo.sqlite3`. Son respaldos, no proyectos paralelos en ejecución. Las capturas y entregas de los Gates anteriores se conservaron. El informe histórico de procesos Gate 3 se restauró desde su ZIP de entrega; las inspecciones actuales se guardan solo con prefijo gate4.

Se detectaron dos instancias antiguas de Django en 8000. Se verificaron sus rutas y PID, se cerraron únicamente procesos SEMI y se dejó uno actualizado. Vite existente se mantuvo en 5173. El inventario final registra los PID y rutas; no se detuvieron aplicaciones ajenas. Se usaron terminales de herramientas, no una terminal integrada controlada de VS Code.

Abrir `http://127.0.0.1:5173`. Los servidores ya están iniciados al entregar; no lanzar duplicados. Para un arranque posterior, desde la carpeta SEMI:

```powershell
# Terminal 1
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

```powershell
# Terminal 2
Set-Location frontend
npm.cmd run dev
```

No ejecutar semillas sobre los datos actuales. No se necesita Docker, Internet para la operación local, ni hardware para la demostración.

Pruebas desde SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar --verbosity 2
Set-Location frontend
npm.cmd run build
npm.cmd run test:e2e
```

Playwright arranca y cierra sus servidores temporales y prepara solo `e2e.sqlite3`. No ejecutar manualmente `prepare_e2e` contra datos de uso. Para restaurar un checkpoint, detener primero los servidores y respaldar cambios posteriores; no copiar una SQLite antigua encima de registros nuevos sin decisión explícita.

## Limitaciones y siguiente validación

La automatización verifica que los pasos y controles funcionan, **no que un agricultor real los entienda sin ayuda**. No se realizó una sesión con una persona no técnica, un ensayo con un teléfono físico ni una certificación de accesibilidad. Esas validaciones siguen pendientes y deben registrar tiempo, dudas, errores y necesidad de ayuda.

El sistema sigue siendo local y demostrativo, sin autenticación para un despliegue público. Los recorridos demo antiguos se conservan por ID en SQLite; no existe un archivo visual de todos los recorridos ni limpieza automática de historia. El papel de los sectores es organizativo y la lista de asociaciones no reconstruye la ubicación física de muestras antiguas.

La identificación física de arena/tierra continúa en investigación. El RPLidar A1 mide distancias y no se usó como clasificador de materiales. Se mantuvieron mock, replay y USB diagnóstico, sin abrir ni activar el sensor físico. NPK real, calibración, precisión y validación agronómica siguen pendientes; no se añadieron umbrales de suficiencia.

Los motores no están habilitados. Driver, corrientes, alimentación aproximada de 24 V, reguladores, esquema/pines, parada física, watchdog local de firmware, latencias, pendientes y distancia de frenado requieren validación y autorización independientes. No hay GPIO/PWM, maniobras automáticas, SLAM ni geofence manual.

Siguiente paso recomendado: observar a una persona no técnica completar el recorrido sin instrucciones previas, registrar dónde necesita ayuda y ajustar solo esos puntos. Después, ensayar por separado un método defendible de detección de superficies sin actuadores. No se inició el Gate 5.
