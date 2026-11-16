# SEMI — Gate 4

Configuración en cuatro etapas, sectores opcionales por nombre y lugares de medición con o sin ubicación. La pantalla Datos consulta resultados e historial del lugar elegido. El ensayo de superficies está separado del cafetal.

**Leer primero [docs/GATE4.md](docs/GATE4.md)**: cambios, migraciones, contratos, preservación, pruebas y límites. No ejecutar semillas sobre la base actual. La migración conserva los datos y el progreso de Gates anteriores.

Abrir `http://127.0.0.1:5173`. Backend en `127.0.0.1:8000`; no iniciar servidores duplicados si ya están activos. El control físico y la clasificación de materiales siguen bloqueados. La prueba de arena es exclusivamente simulada.

Las instrucciones históricas siguientes se conservan; GATE4.md prevalece para esta entrega.

---

# SEMI — Gate 3

Primera instalación guiada, terrenos y zonas descriptivas, puntos visuales y primera lectura simulada. El recorrido demo se puede repetir en un terreno aislado sin borrar registros. El ensayo de arena o pérdida de detección detiene únicamente el simulador.

**Leer primero [docs/GATE3.md](docs/GATE3.md)**: uso en sustentación, migraciones, contratos, evidencia, pruebas y límites. Se conserva la base de Gates anteriores. No ejecutar semillas sobre los datos actuales. Un inicio vacío no necesita semilla.

API local en `127.0.0.1:8000`, Vite en `127.0.0.1:5173`; no iniciar duplicados si ya están activos. E2E usa otra SQLite y servidores temporales. Motores y clasificación física de superficies siguen bloqueados. El diagnóstico A1 no se inicia automáticamente.

Las instrucciones históricas siguientes se conservan; GATE3.md prevalece para esta entrega.

---

# SEMI — Gate 2

El proyecto existente ha evolucionado: control compacto sin scroll, tema claro/oscuro/sistema, puntos persistentes y gráficas por ubicación, diagnóstico LiDAR USB opcional y supervisor C++ con salida falsa.

**Leer primero [docs/GATE2.md](docs/GATE2.md)**: decisiones, API adicional, ejecución, pruebas y límites físicos. Motores del vehículo bloqueados. El lector USB nunca se inicia automáticamente; no fue probado con un A1 físico.

Los comandos de inicio del Gate 1 siguen funcionando; ejecutar migrate antes de iniciar. Playwright inicia ahora sus propios servidores 8002/5174 y usa e2e.sqlite3, sin contaminar demo.sqlite3. La documentación de Gate 1 que sigue es histórica; GATE2.md prevalece para pruebas e integración preparatoria.

---

# SEMI — Gate 1

Sistema Eficiente de Monitoreo Inteligente. MVP local de demostración para un vehículo agrícola de orugas. **No controla hardware físico.**

## Funcionalidad

- Inicio, Control, Datos y Estado, adaptados de los wireframes originales de Figma.
- Django + REST Framework + SQLite; React + TypeScript + Vite + Tailwind.
- Muestras NPK y humedad persistentes, historial, gráfica temporal y parcela esquemática manual.
- Radar polar con 120 puntos LiDAR mock. Sin SLAM, cámara ni navegación automática.
- Control diferencial simulado mediante pulsación mantenida, liberación, teclado y táctil.
- Escenarios: conectado, desconectado, sin datos, obsoleto y error de adquisición.
- Todo dato de prueba se identifica como mock/demostración. Los valores ausentes son null.

## Requisitos

Windows, Python 3.12+, Node.js 24 LTS y npm. Internet se necesita para instalar dependencias; la operación usa recursos locales, incluidas las fuentes. No se requieren Docker, Redis, PostgreSQL ni servicios externos.

Versiones instaladas y verificadas: Python 3.12.3, Node 24.18.0, npm 11.16.0; Django 5.2.19, DRF 3.18.3, React 19.3.1, Vite 8.3.8, Tailwind 4.3.5. Los locks registran las dependencias resueltas.

## Instalación reproducible en PowerShell

Abre una terminal en esta carpeta `SEMI`. No es necesario activar el entorno virtual.

```powershell
python -m venv .venv
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-lock.txt
.\.venv\Scripts\python.exe backend\manage.py migrate
.\.venv\Scripts\python.exe backend\manage.py seed_demo
Set-Location frontend
npm.cmd ci
```

Si el entorno o `.env` ya existen, consérvalos; no vuelvas a copiarlos encima sin revisar. `seed_demo` actualiza 12 muestras identificadas sin duplicarlas ni borrar muestras creadas desde la interfaz. Sus horas se actualizan al momento de la carga.

## Iniciar

Terminal 1, desde `SEMI`:

```powershell
.\.venv\Scripts\python.exe backend\manage.py runserver 127.0.0.1:8000 --noreload
```

Terminal 2, desde `SEMI`:

```powershell
Set-Location frontend
npm.cmd run dev
```

Abre <http://127.0.0.1:5173>. La API está en <http://127.0.0.1:8000/api/health/>. El frontend llama rutas `/api/` mediante el proxy local de Vite; no necesita CORS abierto.

El simulador vive en memoria en **un único proceso Django**. Usa `--noreload`; no emplees varios workers en este gate. Reiniciar Django conserva SQLite y reinicia el estado de control detenido. Esta configuración de desarrollo no es un despliegue de producción.

## Acceso desde un teléfono en la red local

Es opcional y requiere habilitarlo conscientemente. No se publica en Internet. En `.env`, añade la IP LAN del computador a `DJANGO_ALLOWED_HOSTS` y el origen completo del frontend a `DJANGO_CSRF_TRUSTED_ORIGINS`; por ejemplo `http://192.168.1.20:5173`. Conserva localhost si lo utilizas.

Inicia Django con `runserver 0.0.0.0:8000 --noreload` y Vite con `npm.cmd run dev -- --host 0.0.0.0`. Abre desde el teléfono `http://IP-DEL-PC:5173`, conectado a la misma Wi-Fi. La IP del ejemplo no se presume asignada. No desactives protecciones del sistema ni abras puertos del router hacia Internet. El MVP no tiene autenticación de usuarios y solo debe exponerse en una red de demostración controlada.

El funcionamiento responsive se ha probado con emulación de navegador; una prueba sobre un teléfono físico y la Wi-Fi de la finca permanece pendiente.

## Datos y pruebas

La base local se crea en `backend/demo.sqlite3` y no se versiona. Para comenzar con una base vacía sin eliminar la actual, define otro nombre en `SEMI_DATABASE`, ejecuta `migrate` y omite `seed_demo`.

```powershell
# Desde SEMI
.\.venv\Scripts\python.exe backend\manage.py check
.\.venv\Scripts\python.exe backend\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture --verbosity 2

# En otra terminal con los dos servidores iniciados:
Set-Location frontend
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd run test:e2e
```

Las pruebas E2E agregan muestras explícitamente etiquetadas y eventos de demostración a la base activa. Para aislarlas, usa una base de prueba con `SEMI_DATABASE`. El informe HTML queda en `frontend/playwright-report/index.html` y las capturas en `docs/evidence/`.

## Seguridad y límites

`SEMI_PROVIDER` solo acepta `mock`; otro valor impide arrancar. El endpoint de comandos rechaza `mode=hardware`. No hay dependencias seriales, GPIO, SDK de motores ni un interruptor que active movimiento físico. Las variables de futuro transporte LiDAR son descriptivas y no abren conexiones.

La caducidad del simulador se evalúa en cada observación o comando, sin un motor físico ni un supervisor de tiempo real. **No equivale a firmware de seguridad.** La integración de motores exige identificar driver, tensiones, corrientes, batería y protecciones, y autorización en un gate posterior.

## Documentación

- `docs/ARCHITECTURE.md`: capas, polling y límites de adaptadores.
- `docs/API_CONTRACTS.md`: endpoints, JSON, unidades y errores.
- `docs/HARDWARE_STATUS.md`: inventario confirmado y bloqueos.
- `docs/FIGMA_AUDIT.md`: referencia original, cambios y límites de fidelidad.
- `docs/ROADMAP.md`: aceptación y Gate 2 recomendado.
- `docs/TEST_RESULTS.md`: pruebas ejecutadas y limitaciones.

No se avanzó al Gate 2. Git se inicializó en esta carpeta, sin commits automáticos.
