# SEMI — Gate 3: primera instalación y maqueta experimental

Entrega del 15 de noviembre de 2026. Se evolucionó la carpeta SEMI existente. No se creó otro workspace, no se ejecutaron semillas sobre la SQLite principal y no se abrió ningún dispositivo físico.

## Resultado funcional

- Asistente de siete pasos: bienvenida, terreno, zonas descriptivas, lugares para medir, comprobación demostrativa, primera lectura sintética y finalización.
- Un terreno nuevo sin configuración entra automáticamente en el asistente. Los terrenos existentes se conservan como configurados; no se obliga a repetir su instalación.
- Nombre del terreno, zonas, puntos, lecturas, paso actual y finalización persistidos en SQLite. El cultivo está fijado a café arábica; no se solicitan especie, variedad, GPS, umbrales ni protocolos.
- Posición de puntos mediante clic, toque o flechas del teclado. Se pueden crear, ajustar y asociar a una zona. Los ejemplos P1/P2 son opcionales y no constituyen un protocolo agronómico.
- Muestras asociadas mediante FK al punto. P1 puede tener una lectura y P2 seguir sin muestras. Historial y gráfica conservan el filtro por ubicación.
- Claro, oscuro y sistema conservados. El asistente usa tipografía de 17 px, botones de al menos 48 px, foco visible, etiquetas, Volver y Salir por ahora.
- Repetir bienvenida crea un terreno de demostración vacío distinto cada vez. Volver a mis datos recupera el terreno principal.
- Ensayo explícito de tierra, arena, superficie desconocida o pérdida de detección. Arena y pérdida ordenan STOP al simulador. La respuesta a desconocida es configurable y conservadora por defecto. Tierra no inicia movimiento: el operador debe mantener un mando.
- No se calculan rutas, distancias reales, GPS, clasificación de materiales ni aptitud nutricional del suelo.

## Cómo presentar la sustentación

1. Abrir `http://127.0.0.1:5173` y elegir **Repetir bienvenida · demo aislada**.
2. Comenzar, nombrar **Prueba de tierra y arena**, continuar y usar el ejemplo de tierra y arena.
3. Añadir dos puntos de ejemplo o colocarlos tocando el esquema. Se pueden ajustar sin introducir números. Las dos mitades solo ilustran categorías manuales; no representan límites físicos medidos.
4. Continuar por el checklist de demostración. En la primera medición elegir P1 y **Tomar medición de prueba**. La captura exige que el simulador esté detenido.
5. Finalizar y elegir **Ver mis puntos**. En Datos comprobar P1 con una muestra y P2 sin lecturas. La gráfica conecta únicamente muestras del punto seleccionado.
6. Abrir **Ensayo tierra y arena · solo simulación**. Elegir Tierra permite conducir manualmente en el simulador. Elegir Arena muestra advertencia y STOP lógico; no envía reversa ni giro.
7. Probar Pérdida de detección: no se sustituye el dato por tierra. Elegir desconocida permite demostrar la política conservadora.
8. Repetir bienvenida inicia otro recorrido vacío. Los datos anteriores permanecen guardados. **Volver a mis datos** no borra nada.

Los borradores de texto se guardan al pulsar Guardar o Continuar. Un paso guardado se reanuda al recargar; un texto todavía sin guardar puede perderse. Salir por ahora permite consultar la aplicación y la próxima recarga reanuda el paso pendiente. La repetición demo requiere `DEBUG=True`; fuera de desarrollo la API la rechaza con 403.

## Modelos y migraciones

Se mantiene `Sample` y su FK a `SamplingPoint`; no se duplica el modelo de lecturas.

| Entidad | Evolución |
|---|---|
| Plot | Nombre, cultivo fijo, indicador demo, paso, finalización y política/estado de ensayo |
| TerrainZone | FK al terreno, nombre y categoría descriptiva soil/sand/other |
| SamplingPoint | FK opcional a terreno y zona, código; conserva nombre, posición y fecha existentes |
| Sample | Sin cambios destructivos; conserva fecha, valores, unidades, origen, validez y FK al punto |

El perfil de cultivo y el estado de onboarding se guardan en Plot para evitar tablas sin uso adicional. No existe un selector de especie. La referencia a un sensor NPK físico sigue pendiente de identificación; el proveedor actual genera exclusivamente muestras sintéticas.

- `0003_plot_samplingpoint_code_samplingpoint_plot_and_more`: añade tablas y campos inicialmente opcionales.
- `0004_preserve_existing_installation`: asigna los puntos existentes a **Mi terreno**, mantiene todos sus IDs, campos anteriores y relaciones, y marca esa instalación como completada. Si no hay puntos existentes, no crea un terreno: se presenta la primera instalación.
- No hay eliminación de tablas ni muestras. La migración de datos tiene reversión sin borrado; no debe usarse para restaurar versiones anteriores sin el checkpoint correspondiente.

SQLite principal después de la comprobación HTTP: **16 muestras, 8 puntos, 2 terrenos**. Son las **15 muestras y 6 puntos originales sin cambios en sus campos anteriores**, más un terreno demo con dos puntos y una lectura creados intencionadamente para verificar la entrega. `PRAGMA integrity_check = ok`. Ver `gate3-data-preservation.json`.

## Arquitectura y contrato adicional

Se mantiene Django/DRF, SQLite, React/TypeScript/Vite/Tailwind y polling HTTP. No se añadieron servicios ni dependencias de ejecución para este gate.

`Installation.tsx` coordina el asistente y envuelve las cuatro pantallas existentes. Los contratos tipados de configuración están en `types/setup.ts`. El adaptador HTTP añade `X-SEMI-Plot` con el ID guardado localmente. Al cambiar de recorrido se desmontan las pantallas previas; al volver a los datos principales se recarga el contexto.

`GET /api/setup/` devuelve `{schema_version: '1.0', mode: 'demonstration', data: Plot|null}`. Plot incluye `id`, `name`, `crop`, `demo`, `step`, `completed`, `surface`, `conservative`, `zones` y `points` con su última muestra. El paso solo admite enteros de 1 a 7.

`POST /api/setup/` usa CSRF y las siguientes acciones:

| action | Campos principales | Resultado |
|---|---|---|
| start | ninguno | Recupera o crea configuración principal |
| demo | ninguno | Nuevo terreno demo vacío; solo desarrollo |
| save | name, step | Guarda nombre/progreso |
| zone | name, category, zone opcional | Crea o edita zona del terreno actual |
| point | x, y, name opcional, zone opcional, point opcional | Crea o ajusta punto propio |
| capture | point | Genera muestra sintética del punto propio, con simulador en STOP |
| complete | ninguno | Guarda finalización |
| surface | surface, conservative | Modifica únicamente el ensayo de un terreno demo |

`x/y` son parámetros internos del esquema visual entre 0 y 100, no GPS ni metros. El asistente no exige escribirlos. La API conserva los nombres únicos anteriores; añade `display_name`, `code` y `zone` de solo lectura al contrato de puntos. La interfaz oculta el sufijo interno de aislamiento de los puntos nuevos.

Validación incorrecta: 400; intento demo fuera de desarrollo/operación física: 403; contexto inexistente o punto ajeno en lectura: 404; movimiento bloqueado por ensayo: 409 (`surface_demo_stop`). Los 404 de pruebas negativas son intencionados; los recorridos positivos del navegador vigilan y rechazan cualquier respuesta API 404.

Sin cabecera se usa el terreno principal cuando existe. Con cabecera, puntos, últimas lecturas, historial y capturas se filtran por terreno, y se rechazan asociaciones ajenas. Cada demo dispone de un simulador de movimiento independiente. Las transiciones de superficie y comandos se serializan con el bloqueo del simulador; la política se recupera de SQLite tras reiniciar. El estado de movimiento arranca detenido.

Este aislamiento es de escenarios en una aplicación local, **no autenticación ni separación segura entre usuarios hostiles**. El diagnóstico USB/replay LiDAR sigue siendo un servicio compartido del equipo; no se abre un lector por terreno. No exponer el servidor en Internet. El registro de diagnóstico general sigue siendo de la instalación; la actividad global no se muestra como actividad propia de un lote demo vacío.

No se implementó limpieza automática de demos: cada repetición conserva registros. Los recorridos antiguos permanecen en SQLite, identificados por su ID; la interfaz recupera el recorrido seleccionado en ese navegador o el terreno principal. Un selector/archivo de recorridos antiguos puede incorporarse posteriormente sin borrar historia.

## Estabilización de procesos y 404

Se comprobaron PID, línea de comando y directorio real mediante información del sistema. Se encontraron instancias anteriores de SEMI en 8000 y 8010, y Vite en 5173. Se cerraron únicamente las instancias verificadas del proyecto. Windows no permitió una señal ordenada de consola a los procesos antiguos; se utilizó terminación dirigida por PID. SQLite se había respaldado antes y su integridad se verificó después.

Quedaron una instancia Django en `127.0.0.1:8000` y una Vite en `127.0.0.1:5173`, con proxy explícito `/api` hacia 8000. Los puertos 8010/5175 y los temporales E2E no deben permanecer escuchando. La instantánea final con PID y rutas está en `gate3-processes.json`.

`GET /api/sampling-points/` y la lectura individual respondieron 200 a través del proxy final. Se verificó creación y lectura en un lote demo aislado de la misma base, además de las pruebas E2E en otra SQLite.

Limitación de herramientas: no había un canal fiable para ejecutar comandos en las terminales integradas de VS Code ni consultar sus búferes sin guardar. Se inspeccionaron los archivos de disco, Git, procesos y migraciones, y se utilizaron terminales de herramientas. No se manipuló la interfaz de VS Code ni se afirmó haber verificado sus cambios sin guardar. El checkpoint captura el estado en disco.

## Pruebas ejecutadas

| Verificación | Resultado y evidencia |
|---|---|
| Django check | Sin incidencias; `gate3-checks.txt` |
| Migraciones | 0001–0004 aplicadas; sin cambios de modelo pendientes |
| Django agricultura/LiDAR | **40 pruebas aprobadas**; SQLite temporal en memoria; `gate3-backend.txt` |
| Frontend TypeScript + Vite | Compilación aprobada; `gate3-build.txt` |
| Chromium Playwright | **27 pruebas aprobadas**, incluyen las 18 del Gate 2 y 9 del Gate 3; `gate3-browser.txt` |
| Onboarding responsive | Siete pasos, P1 con lectura/P2 vacío, claro y oscuro, anchuras 360/390/768/1440; sin desbordamiento horizontal |
| Control heredado | Radar y mandos visibles, STOP accesible, objetivos >=44 px; 360×640, 390×844, 768×900, 1440×900 y horizontal 740×360 |
| Interacciones heredadas | Mouse, táctil, teclado, cancelación, foco, pestaña, desconexión, liberación, caducidad/secuencias |
| Tema | Persistencia/sistema y contraste de tokens existentes >=4.5, pruebas heredadas; revisión visual de pasos claros/oscuros |
| Primera instalación | API vacía real probada en Django; entrada automática de UI probada con respuesta inicial vacía interceptada; escrituras completas en escenarios demo reales de E2E |
| Salida y reanudación | Salir, recargar y recuperar paso/nombre guardados |
| Aislamiento | Nuevo recorrido vacío, datos previos preservados, rechazo de punto ajeno, consultas/contexto separados |
| Superficies | Arena y pérdida -> STOP, desconocida conservadora bloquea, política opcional permite continuar, tierra no inicia movimiento |
| HTTP local final | Proxy, creación/lectura, captura, historial P1/P2, STOP y rechazo físico 403; `gate3-live-api.json` |
| Supervisor nativo heredado | Ejecutable C++ fake aprobado; tiempo monotónico, renovación, caducidad, secuencias, STOP/reinicio y fallos; `gate3-supervisor.txt` |
| Integridad SQLite | Campos originales comparados fila por fila contra checkpoint; integrity_check ok |

Las pruebas C++ conservan el supervisor local preparado en Gate 2 y su salida falsa. El máximo retraso de caducidad de 6 ms corresponde al calendario determinista de ese test, **no a una medición física ni al ESP32 real**. Django continúa siendo un simulador de un solo proceso; la parada de motores futuros requiere watchdog local en firmware, no este servidor.

Se reutilizaron la identidad visual y los tokens existentes; no se afirmó una nueva inspección de Figma. Las capturas originales Gate 1/2 se conservaron. Las nuevas están en `evidence-gate3` y la regresión visual en `evidence-gate3-regression`; Playwright escribe ahora en `playwright-report-gate3`. E2E usa `e2e.sqlite3`, nunca la base principal; el comando de preparación solo permite vaciar ese archivo de prueba. No se ejecutó `seed_demo` contra la base principal.

No se realizó un estudio con agricultores, una prueba sobre teléfono físico, medición exhaustiva de contraste de cada combinación visual ni prueba física de sensores/motores. La revisión de accesibilidad es técnica y de navegador, no una certificación.

## Ejecución en Windows

Los servidores de esta entrega ya están iniciados localmente. No volver a lanzar otros sobre los mismos puertos. Para un arranque posterior, abrir dos terminales integradas en el mismo proyecto SEMI:

```powershell
# Terminal 1, desde SEMI. No volver a ejecutar semillas sobre datos actuales.
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

```powershell
# Terminal 2, desde SEMI
Set-Location frontend
npm.cmd run dev
```

Abrir `http://127.0.0.1:5173`. No hace falta Internet para operar con las dependencias ya instaladas. Si falta instalar dependencias, conservar `.env` y usar los requirements/lock existentes y `npm.cmd ci`; no reemplazar configuraciones ni recrear una base de producción. Una instalación nueva vacía no necesita semilla: el asistente crea sus propios datos.

Pruebas, desde SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar --verbosity 2
Set-Location frontend
npm.cmd run build
npm.cmd run test:e2e
```

Playwright arranca y cierra sus propios servidores 8002/5174, utiliza Chromium instalado y SQLite E2E. No necesita el A1. Si esos puertos están ocupados, identificar propietario y ruta antes de cerrar procesos; no reutiliza silenciosamente un servidor ajeno.

## Checkpoints y archivos

- Antes de cambios: `outputs/SEMI-checkpoint-before-gate3/source.zip` y copia consistente `demo.sqlite3`.
- Entrega: `outputs/SEMI-Gate3.zip` (fuentes/documentación/evidencias, sin entornos, puertos seriales ni secretos), más `outputs/SEMI-checkpoint-gate3-final/demo.sqlite3` como copia consistente separada.
- Archivo de cambios contra el checkpoint: `docs/CHANGES_GATE3.txt`. Git ya existía y todos los archivos base estaban sin seguimiento; no se hicieron commits ni se sustituyó la historia.

Los ZIP son respaldos, no nuevos proyectos en ejecución. Restaurar únicamente en la carpeta original, con los servidores detenidos y conservando primero cualquier cambio posterior. No restaurar la SQLite anterior sobre registros nuevos sin una decisión explícita: la entrega no hace ese reemplazo.

## Límites y próxima integración

**Funcional:** persistencia, asistente, puntos, historial/gráfica por ubicación, recuperación, temas y control simulado. **Demostrativo:** batería, NPK/humedad, radar mock/replay, tierra/arena y STOP del ensayo. **Pendiente de hardware:** adquisición física A1, clasificación de superficies, NPK real, posicionamiento y locomoción. **Pendiente agronómico:** unidades reales, calibración, validación de precisión y procedimiento de muestreo; no hay diagnósticos de fertilidad.

Para la maqueta faltan medidas del vehículo, orugas y base, separación de materiales, espacio de giro, distancia de detención, iluminación/humedad y procedimiento/ubicación/profundidad de la sonda. La posición del esquema no se convierte en metros y no impone una distancia mínima entre puntos.

Antes de movimiento físico: identificar driver, motores/corrientes, batería/reguladores, esquema/pines, habilitación y STOP independiente, parada física accesible, firmware con watchdog local, latencias, área contenida y supervisión humana. Se mantiene bloqueado GPIO/PWM; no se asume que TB6612FNG admita 24 V.

Siguiente incremento recomendado: validar el recorrido con una persona ajena al desarrollo y medir la maqueta; después seleccionar y ensayar un método independiente de detección de superficies, con registro de aciertos/fallos y sin actuadores. Mantener el A1 como distancias relativas y validar su adquisición USB solo con autorización. No se inició otro gate ni se activó el A1 físico.
