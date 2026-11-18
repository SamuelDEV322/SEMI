# SEMI — Sistema Eficiente de Monitoreo Inteligente

Plataforma local en desarrollo para monitorear suelo de cafetales de **Coffea arabica L.** y preparar la teleoperación manual supervisada de un vehículo de orugas. La base del MVP corresponde al **Gate 4**, con un perfil operativo que prepara la adquisición real sin controles de ensayo en la interfaz del agricultor.

**Las mediciones de demostración son sintéticas. Los motores físicos no están habilitados.** No hay navegación autónoma, SLAM, georreferenciación ni clasificación física de tierra/arena validada.

## Alcance actual

- Inicio, Control, Datos y Estado, con interfaz responsive y temas claro, oscuro y sistema.
- Configuración inicial en cuatro etapas, reanudable: bienvenida, cafetal, lugares para medir y revisión/primera medición opcional.
- Sectores descriptivos opcionales, con renombrado, archivo, eliminación segura de sectores vacíos y conservación de asociaciones.
- Puntos P1/P2 con sector y posición relativa opcionales. No son destinos automáticos ni restringen la circulación.
- NPK y humedad persistentes en SQLite, con resultados e historial por punto. El perfil operativo solo muestra filas de procedencia real; no fabrica lecturas si falta la sonda.
- Radar LiDAR configurado para la fuente real USB por defecto; lector separado con inicio manual. Adquisición física pendiente de validación en el prototipo.
- Control manual preparado visualmente, deshabilitado en operación hasta integrar el ESP32. El perfil de desarrollo conserva pulsación mantenida, liberación, teclado/táctil y caducidad del simulador.
- Recorridos demo aislados y ensayo de superficies disponibles únicamente al configurar explícitamente el perfil de desarrollo. No hay selector de fuentes en la UI, ni siquiera en ese perfil.

## Tecnologías y estructura

Django + Django REST Framework + SQLite; React + TypeScript + Vite + Tailwind CSS. HTTP con polling; no requiere Docker, PostgreSQL, Redis, Celery ni nube.

```text
SEMI/
├── backend/
│   ├── config/                 # Configuración, URLs y vistas API
│   ├── apps/                   # Agricultura, robot, telemetría y LiDAR
│   ├── adapters/               # Contratos, simulación, replay y diagnóstico A1
│   ├── requirements*.txt
│   └── manage.py
├── frontend/
│   ├── src/                    # Pantallas, componentes, hooks y contratos tipados
│   ├── public/                 # Recursos locales necesarios para la UI
│   ├── e2e/                    # Pruebas Playwright
│   ├── package.json
│   └── package-lock.json
├── firmware/                   # Supervisor de prueba con salida falsa; sin GPIO/PWM
├── docs/                       # Arquitectura, API, hardware y Gates históricos
├── .env.example
└── README.md
```

## Requisitos en Windows

- Python 3.12 y módulo `venv` (verificado con 3.12.3).
- Node.js 24 y npm (verificados con Node 24.18.0 y npm 11.16.0).
- Git y PowerShell.
- Internet para descargar dependencias y Chromium durante la instalación. La operación posterior es local.

Las versiones del proyecto se conservan en requirements y `package-lock.json`; no es necesario actualizarlas para iniciar. No cambiar la venv o `node_modules` de servidores que estén activos: detenerlos conscientemente antes de reinstalar dependencias en esa misma ubicación.

## Backend: instalación desde cero

Desde una copia/clon del repositorio, abrir PowerShell **en la carpeta SEMI**. En una instalación nueva:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
.\.venv\Scripts\python.exe backend\manage.py migrate
```

Si `.venv`, `.env` o la base ya existen, conservarlos y revisar antes de reemplazarlos. No hace falta activar la venv ni cambiar la política de ejecución de PowerShell.

Dependencias:

| Archivo | Uso |
|---|---|
| `backend/requirements.txt` | Directas de ejecución: Django, DRF y python-dotenv |
| `backend/requirements-lock.txt` | Cierre mínimo de ejecución, con asgiref, sqlparse y tzdata; no es un freeze de todo el equipo |
| `backend/requirements-dev.txt` | Runtime y Black; las pruebas Django usan su runner y la biblioteca estándar |
| `backend/requirements-lidar.txt` | Runtime y pyserial, opcional para diagnóstico USB |
| `firmware/requirements-test.txt` | Compilador opcional del supervisor C++ de prueba, no necesario para el MVP web |

Para herramientas de desarrollo, desde SEMI:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
```

Solo si se va a preparar el diagnóstico USB autorizado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lidar.txt
```

Instalar pyserial no abre puertos ni inicia el sensor. La adquisición física requiere otra autorización y la revisión de dispositivo/kit.

## Frontend: instalación

```powershell
# Desde SEMI
Set-Location frontend
npm.cmd ci
```

`npm ci` utiliza el lock incluido. No sustituirlo por una actualización masiva de paquetes. Scripts existentes:

| Comando desde frontend | Función |
|---|---|
| `npm.cmd run dev` | Vite en 127.0.0.1:5173 |
| `npm.cmd run build` | Comprobación TypeScript y compilación Vite |
| `npm.cmd run preview` | Previsualización de dist en 127.0.0.1:4173 |
| `npm.cmd run test:e2e` | Suite Chromium/Playwright con backend de prueba aislado |
| `npm.cmd run format` | Formatea código y pruebas; modifica archivos, no es una comprobación de solo lectura |

## SQLite y migraciones

Por defecto se utiliza `backend/demo.sqlite3`. El archivo local y sus WAL/SHM/journals/respaldo están ignorados en Git. **La base actual se conserva localmente, no se sube al repositorio.**

Una copia nueva crea su esquema con `migrate` y entra al asistente sin datos históricos. No necesita semillas: el usuario crea el cafetal y sus puntos. Las lecturas físicas permanecerán no disponibles hasta integrar el sensor. No ejecutar `seed_demo` sobre una base en uso; sus datos identificados se actualizan al sembrar.

Las migraciones forman parte del repositorio. La 0007 amplía la restricción de procedencia para admitir `mock`, `replay` y `real`, sin convertir registros anteriores en reales. Las 0005/0006 conservan las filas antiguas y transforman sectores/progreso para Gate 4. Antes de aplicar futuras migraciones a datos importantes, guardar una copia SQLite consistente fuera de Git.

## Configuración local

Django lee `.env` en la raíz de SEMI. Las variables del proceso tienen prioridad sobre ese archivo. Vite también utiliza la raíz como `envDir`.

| Variable | Efecto y valor local de referencia |
|---|---|
| `DJANGO_DEBUG` | `1` para desarrollo; por sí solo no habilita herramientas de ensayo |
| `DJANGO_SECRET_KEY` | Marcador público solo de demostración en `.env.example`; nunca usarlo como secreto de producción |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver`; lista separada por comas |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes completos del frontend; incluye localhost/127.0.0.1 en 5173 |
| `SEMI_DATABASE` | `demo.sqlite3`, ruta relativa a backend; los tests E2E fuerzan `e2e.sqlite3` |
| `SEMI_MODE` | `operational` por defecto; `demonstration` solo para desarrollo/pruebas |
| `SEMI_LIDAR_SOURCE` | `real` en operación; `mock`/`replay` solo en perfil de demostración; requiere reiniciar Django |
| `SEMI_DEV_TOOLS` | `0`; `1` muestra ensayos solo si también hay DEBUG y perfil demonstration |
| `SEMI_LIDAR_DIAGNOSTICS` | `0` por defecto; `1` solo autoriza el diagnóstico local, no inicia el lector |
| `SEMI_LIDAR_SPOOL` | Vacío usa `backend/runtime/lidar-latest.json`; intercambio del último escaneo, sin almacenar cada punto en SQLite |
| `VITE_BACKEND_TARGET` | Proxy HTTP de desarrollo/preview, por defecto `http://127.0.0.1:8000` |

No colocar secretos en variables `VITE_*`, código, commits ni `.env.example`. `.env` es privado y está ignorado. Las antiguas variables `SEMI_PROVIDER` y `SEMI_FUTURE_LIDAR_*` no se consumen: se retiraron del ejemplo, sin alterar configuración activa.

Esta configuración es local. Una futura producción necesita configuración propia de secretos, hosts, HTTPS, autenticación y servidor de despliegue; no está resuelta cambiando únicamente `DEBUG=0`. Este repositorio no realiza despliegues.

## Ejecución local

No iniciar duplicados si los puertos ya están ocupados. No detener procesos ajenos para liberar un puerto.

Terminal 1, desde SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

Terminal 2, desde SEMI:

```powershell
Set-Location frontend
npm.cmd run dev
```

Abrir [SEMI local](http://127.0.0.1:5173). La API responde en [health](http://127.0.0.1:8000/api/health/). Vite envía `/api` al backend mediante proxy; no hace falta abrir CORS indiscriminadamente.

Las fuentes se fijan al iniciar Django y no pueden cambiarse desde el navegador. El perfil operativo utiliza el último escaneo USB sin abrir puertos y comunica honestamente los componentes no integrados. El simulador de desarrollo es de **un solo proceso Django**. Mantener `--noreload` y no utilizar múltiples workers. Reiniciar el proceso conserva SQLite y vuelve a STOP lógico. Los servidores de desarrollo no son servidores de producción.

## Comprobaciones y pruebas

Desde SEMI:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar --verbosity 2
```

Desde frontend, con dependencias instaladas:

```powershell
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
# Ejecutar después, nunca simultáneamente: comparten e2e.sqlite3
npm.cmd run test:mvp
```

Django usa su base de pruebas temporal. Playwright crea servidores temporales en 8002/5174, fuerza `backend/e2e.sqlite3` y los cierra al terminar. Su preparación puede vaciar **esa base de prueba**, nunca debe apuntar a datos de uso. La suite activa ejecuta Gate 2 adaptado y Gate 4; los specs antiguos se conservan como historia. La suite `test:mvp` verifica el perfil operativo en 8003/5175, también sobre e2e.sqlite3. Ambas suites se ejecutan **secuencialmente** y cierran sus servidores temporales. Las pruebas no necesitan hardware.

Los resultados de la revisión para el primer commit están en [docs/REPOSITORY.md](docs/REPOSITORY.md). No confundir pruebas automatizadas con una prueba de usabilidad con un agricultor o con validación física.

## Perfil operativo y pruebas de desarrollo

La instalación normal arranca en `operational` + LiDAR `real` + herramientas deshabilitadas. Si el lector USB no está iniciado, aparece sin lecturas. Si falta el ESP32, no se confirma STOP, conexión ni carga de batería. Si falta la sonda NPK, no se genera una muestra. No hay sustitución automática por datos de prueba.

El frontend consulta las capacidades en `/api/health/`; la autorización también se aplica en Django. Alterar localStorage, el encabezado del lote o enviar un POST de cambio de fuente no habilita simulación ni actuadores. `/api/lidar/source/` responde 405. El registro público tampoco admite autodeclarar valores como lecturas reales.

Para trabajar sobre simulación, configurar **en el servidor**, antes de iniciarlo:

```powershell
$env:SEMI_MODE = 'demonstration'
$env:SEMI_LIDAR_SOURCE = 'mock'
$env:SEMI_DEV_TOOLS = '1'
# Usar una base de pruebas propia, sin reemplazar una que ya tenga datos.
$env:SEMI_DATABASE = 'development.sqlite3'
```

Aplicar migraciones a esa base y ejecutar los mismos comandos de inicio. Las variables duran en esa terminal y tienen prioridad sobre `.env`. `DEBUG=1` también es necesario para mostrar ensayos. Nunca copiar este perfil a una instalación operativa. `MODO DEMOSTRACIÓN` sigue visible cuando se utilizan datos sintéticos; ocultar herramientas no debe ocultar su procedencia.

Los contratos de `RobotProvider`, `TelemetryProvider`, `NPKProvider` y `LidarProvider` separan UI y adquisición. `UnconfiguredRobotProvider` expresa la ausencia de un enlace físico. `LidarSources` lee el último escaneo publicado por `lidar_usb`, conserva mock/replay para pruebas y no mantiene un puerto serial en Django. La integración inalámbrica y los adaptadores ESP32/NPK continúan pendientes; no hay un protocolo inventado para ellos.

La guía de prueba asíncrona para el compañero está en [docs/OPERATING_PROFILE.md](docs/OPERATING_PROFILE.md). No iniciar el lector sin revisar su puerto, revisión y kit compatible: puede girar el motor del propio LiDAR. No controla las orugas.

## Gate 5A/5B: recepción ESP32 en diagnóstico

La nueva app `backend/apps/devices` recibe telemetría/heartbeats autenticados, con sesión, secuencias e idempotencia persistentes. Conserva ADC original y tensión si son enviados; no produce porcentajes calibrados ni NPK. La conexión se muestra como diagnóstico, con movimiento físico bloqueado.

Está **deshabilitada por defecto**. `SEMI_MODE` conserva sus valores; `SEMI_DEVICE_INTEGRATION` solo admite `disabled|diagnostic`. Credenciales por dispositivo en `SEMI_DEVICE_TOKENS`, fuera de Git y del frontend. No hay una opción que habilite control físico.

- [Contrato Gate 5A](docs/GATE5A_CONTRACTS.md): rutas, JSON, autenticación, secuencias, sesiones, vencimientos y fallos.
- [Implementación y ejecución Gate 5B](docs/GATE5B_IMPLEMENTATION.md): registro local, pruebas aisladas y límites.
- Desde SEMI: `.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar apps.devices`.
- Desde frontend: `npm.cmd run test:device`. Ejecutarlo secuencialmente respecto a `test:e2e` y `test:mvp`; comparten únicamente e2e.sqlite3.

El firmware original del compañero no se modifica. La prueba del contrato usa clientes sintéticos; no demuestra un ESP32 conectado. USB/LiDAR conserva su integración separada y su inicio manual.

## Hardware, seguridad y límites

- RPLidar A1 confirmado como componente, sin adquisición física validada en esta entrega. No proporciona por sí solo GPS ni clasificación de materiales.
- NPK/humedad de los Gates anteriores sintéticos y conservados; modelo físico, protocolo, calibración y precisión agronómica pendientes. No hay umbrales de suficiencia/deficiencia.
- Cámara, sensores ambientales e inclinación no confirmados.
- El endpoint de comandos rechaza movimiento físico. No se habilitan GPIO/PWM ni actuadores. El botón web no es una parada física de emergencia.
- La caducidad del simulador no sustituye un watchdog local de firmware. El supervisor C++ conserva una salida falsa y pruebas deterministas, no protección física demostrada.
- Driver, corriente de motores, batería aproximada de 24 V, reguladores, esquema y parada física deben verificarse antes de otra integración. No asumir compatibilidad directa de TB6612FNG con 24 V.
- Aplicación local sin autenticación multiusuario. El contexto por cafetal evita mezclar IDs dentro de una operación, pero no aísla usuarios hostiles. No exponer públicamente.
- Responsive/teclado/táctil se verifican en navegador; siguen pendientes evaluación con una persona no técnica, teléfono físico, red rural y ensayos mecánicos/agronómicos.

## Documentación e historia

- [Arquitectura](docs/ARCHITECTURE.md), [contratos API](docs/API_CONTRACTS.md), [hardware](docs/HARDWARE_STATUS.md) y [roadmap](docs/ROADMAP.md).
- [Gate 4](docs/GATE4.md), [Gate 3](docs/GATE3.md), [Gate 2](docs/GATE2.md), [pruebas históricas](docs/TEST_RESULTS.md) y [referencia Figma](docs/FIGMA_AUDIT.md).
- [README histórico de Gates 1–4](docs/README_HISTORY_GATES_1_TO_4.md). Sus instrucciones antiguas se conservan como historia; este README prevalece para reconstruir el entorno.
- [Política de versionado y validación](docs/REPOSITORY.md).

Los Markdown técnicos, migraciones, pruebas, fixtures JSON y recursos de la interfaz se versionan. Capturas masivas, logs crudos, reportes Playwright, escaneos temporales, ZIP de entregas y bases quedan locales e ignorados. Algunas referencias de los informes históricos apuntan a esas evidencias locales o a entregas fuera del repositorio; las pruebas permiten regenerarlas. No se eliminaron archivos para preparar Git.

## GitHub: primer envío manual

El nombre deseado es **SEMI**. Crear en GitHub un repositorio **privado y vacío**, sin README, licencia ni `.gitignore` remotos iniciales. Desde SEMI, si todavía no existe origin:

```powershell
$githubUser = Read-Host 'Tu usuario de GitHub'
git remote add origin "https://github.com/$githubUser/SEMI.git"
git remote -v
git push -u origin main
```

Si `origin` ya existe, revisar su URL y conservarlo; no añadirlo ni reemplazarlo a ciegas. No utilizar push forzado. El repositorio solo debe enviarse cuando el usuario lo autorice expresamente. Esta revisión no avanza al Gate 5.
