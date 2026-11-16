# SEMI — Sistema Eficiente de Monitoreo Inteligente

Plataforma local en desarrollo para monitorear suelo de cafetales de **Coffea arabica L.** y preparar la teleoperación manual supervisada de un vehículo de orugas. El MVP corresponde al **Gate 4**.

**Las mediciones de demostración son sintéticas. Los motores físicos no están habilitados.** No hay navegación autónoma, SLAM, georreferenciación ni clasificación física de tierra/arena validada.

## Alcance actual

- Inicio, Control, Datos y Estado, con interfaz responsive y temas claro, oscuro y sistema.
- Configuración inicial en cuatro etapas, reanudable: bienvenida, cafetal, lugares para medir y revisión/primera medición opcional.
- Sectores descriptivos opcionales, con renombrado, archivo, eliminación segura de sectores vacíos y conservación de asociaciones.
- Puntos P1/P2 con sector y posición relativa opcionales. No son destinos automáticos ni restringen la circulación.
- NPK y humedad simulados, persistentes en SQLite, con resultados e historial por punto.
- Radar LiDAR mock/replay y adaptador USB de diagnóstico separado, pendiente de validación física.
- Control manual solo en simulación: pulsación mantenida, liberación, teclado/táctil, confirmaciones y caducidad.
- Recorridos demo aislados y ensayo de superficies separado del cafetal; arena/pérdida generan STOP lógico, nunca una maniobra física.

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
- Internet para descargar dependencias y Chromium durante la instalación. La operación demostrativa posterior es local.

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

Una copia nueva crea su esquema con `migrate` y entra al asistente sin datos históricos. No necesita semillas: el usuario crea el cafetal y pide lecturas simuladas. No ejecutar `seed_demo` sobre una base en uso; sus datos identificados se actualizan al sembrar.

Las migraciones forman parte del repositorio. Las 0005/0006 conservan las filas antiguas y transforman sectores/progreso para Gate 4. Antes de aplicar futuras migraciones a datos importantes, guardar una copia SQLite consistente fuera de Git.

## Configuración local

Django lee `.env` en la raíz de SEMI. Las variables del proceso tienen prioridad sobre ese archivo. Vite también utiliza la raíz como `envDir`.

| Variable | Efecto y valor local de referencia |
|---|---|
| `DJANGO_DEBUG` | `1` para desarrollo; habilita recorridos demo de desarrollo |
| `DJANGO_SECRET_KEY` | Marcador público solo de demostración en `.env.example`; nunca usarlo como secreto de producción |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,testserver`; lista separada por comas |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | Orígenes completos del frontend; incluye localhost/127.0.0.1 en 5173 |
| `SEMI_DATABASE` | `demo.sqlite3`, ruta relativa a backend; los tests E2E fuerzan `e2e.sqlite3` |
| `SEMI_PROVIDER` | Solo acepta `mock`; otro valor impide arrancar, no habilita motores |
| `SEMI_LIDAR_DIAGNOSTICS` | `0` por defecto; `1` solo autoriza el diagnóstico local, no inicia el lector |
| `SEMI_LIDAR_SPOOL` | Vacío usa `backend/runtime/lidar-latest.json`; intercambio del último escaneo, sin almacenar cada punto en SQLite |
| `VITE_BACKEND_TARGET` | Proxy HTTP de desarrollo/preview, por defecto `http://127.0.0.1:8000` |

No colocar secretos en variables `VITE_*`, código, commits ni `.env.example`. `.env` es privado y está ignorado. Las antiguas variables `SEMI_FUTURE_LIDAR_*` eran descriptivas y no se consumen: se retiraron del ejemplo, sin alterar configuración activa.

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

El simulador es de **un solo proceso Django**. Mantener `--noreload` y no utilizar múltiples workers. Reiniciar el proceso conserva SQLite y vuelve a STOP lógico. Los servidores de desarrollo no son servidores de producción.

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
```

Django usa su base de pruebas temporal. Playwright crea servidores temporales en 8002/5174, fuerza `backend/e2e.sqlite3` y los cierra al terminar. Su preparación puede vaciar **esa base de prueba**, nunca debe apuntar a datos de uso. La suite activa ejecuta Gate 2 adaptado y Gate 4; los specs antiguos se conservan como historia. Las pruebas no necesitan hardware.

Los resultados de la revisión para el primer commit están en [docs/REPOSITORY.md](docs/REPOSITORY.md). No confundir pruebas automatizadas con una prueba de usabilidad con un agricultor o con validación física.

## Demostración y proveedores

El rótulo **MODO DEMOSTRACIÓN** identifica las lecturas y el movimiento sintéticos. Repetir bienvenida crea otro escenario vacío sin borrar el cafetal principal. Los sectores son organización por nombre; una etiqueta manual nunca es una detección ni un geofence.

Los contratos de `RobotProvider`, `TelemetryProvider`, `NPKProvider` y `LidarProvider` separan UI/servicios de adquisición. Los proveedores mock actuales alimentan contratos tipados comunes. `LidarSources` conserva mock/replay y el lector USB de diagnóstico independiente. La integración inalámbrica y proveedores físicos ESP32/NPK siguen pendientes; no se presentan como funciones implementadas.

## Hardware, seguridad y límites

- RPLidar A1 confirmado como componente, sin adquisición física validada en esta entrega. No proporciona por sí solo GPS ni clasificación de materiales.
- NPK/humedad actuales sintéticos; modelo físico, protocolo, calibración y precisión agronómica pendientes. No hay umbrales de suficiencia/deficiencia.
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

Si `origin` ya existe, revisar su URL y conservarlo; no añadirlo ni reemplazarlo a ciegas. No utilizar push forzado. El push lo realiza el usuario; la preparación local no publica commits ni avanza al Gate 5.
