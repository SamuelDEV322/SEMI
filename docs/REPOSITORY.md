# Repositorio SEMI — baseline Gate 4

## Alcance de esta preparación

Primer versionado estable del proyecto existente. Se conserva la carpeta `.git` y su configuración; al empezar no había commits ni remotos y la rama era master. Se renombró a main sin reescribir historia. Se utiliza la identidad Git ya configurada, sin modificar la configuración global.

El mensaje solicitado del primer commit es `chore: initialize SEMI repository at Gate 4`. La preparación no ejecuta push, despliegue ni publicación. GitHub CLI no estaba disponible en PATH; origin se deja sin configurar. Las instrucciones manuales están en README.

## Qué se versiona

- Código Django/DRF y frontend React/TypeScript, contratos, adaptadores y componentes actuales del Gate 4.
- Todas las migraciones Django y pruebas de agricultura/LiDAR; fixtures JSON del parser/replay.
- package.json, package-lock.json, configuración Vite/Tailwind/TypeScript/Playwright y recursos de interfaz (incluido public/theme.js). Las fuentes y los iconos se reconstruyen con npm ci.
- Requirements directos, cierre mínimo de runtime, desarrollo y transporte USB opcional; requisitos separados del supervisor C++ fake.
- Documentos de arquitectura, API, hardware, Figma, Gates anteriores e historia de cambios. El README anterior se conserva en README_HISTORY_GATES_1_TO_4.md.
- .env.example público, .gitignore y .gitattributes para texto consistente en Windows/Linux.

## Qué queda exclusivamente local

`.venv`, venv, node_modules, cachés, dist/build, SQLite y journals/WAL/SHM/respaldo, `.env` y variantes privadas, logs, runtime LiDAR, reportes Playwright, capturas masivas y entregas/checkpoints generados. También se ignoran el estado local del editor y los archivos del sistema operativo.

Los datos existentes no se borran para ignorarlos. Tampoco se excluyen globalmente imágenes o JSON: el fixture de replay y los recursos necesarios siguen versionados. Los informes históricos pueden apuntar a capturas/logs que permanecen locales o en entregas fuera del repositorio; no son dependencias de ejecución. Las suites pueden regenerar evidencias.

La carpeta temporal .dependency-check solo contiene entornos/instalaciones de comprobación, no otra aplicación ni otro repositorio. Está ignorada. Los logs de esta revisión quedan en docs/repository-checks, también ignorados.

## Dependencias y configuración

Se revisaron imports reales. El runtime Python solo necesita Django, djangorestframework y python-dotenv. requirements-lock.txt conserva ese cierre y asgiref/sqlparse/tzdata; no se ejecutó pip freeze del entorno completo. Black se declara en desarrollo y pyserial se mantiene opcional. psutil y otras herramientas de inspección del equipo no se incorporan como dependencias del backend. No se actualizaron versiones.

Se reconstruyó una venv temporal desde requirements-lock + requirements-dev + requirements-lidar, sin modificar la venv activa. La instalación opcional de pyserial no inicia ningún dispositivo.

npm ci se ejecutó sobre copias únicamente de los dos manifests en una carpeta temporal de dependencias, para no reemplazar node_modules del Vite activo. La instalación terminó correctamente y ambos manifests originales conservaron sus hashes. Scripts dev/build/test:e2e/format existentes se conservaron sin cambios de comportamiento.

.env.example documenta únicamente variables consumidas. Las variables descriptivas SEMI_FUTURE_LIDAR_* se retiraron del ejemplo porque no se leen. El marcador DJANGO_SECRET_KEY del ejemplo y el fallback de settings son públicos, solo de demostración; no son claves reales de producción. No se modificó un .env activo ni se generó un secreto de producción.

## Comprobaciones de esta revisión

| Comprobación | Resultado |
|---|---|
| Reconstrucción Python temporal | Runtime, desarrollo y opcional USB instalados correctamente |
| pip check | Sin dependencias rotas |
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Tests Django con la venv reconstruida | 49 aprobados; base temporal en memoria |
| npm ci aislado | Correcto, 47 paquetes instalados; lock original sin cambios |
| TypeScript/Vite build | Correcto |
| Playwright Chromium | 29 aprobados; SQLite e2e.sqlite3 y puertos temporales 8002/5174 |

El primer intento offline de npm ci encontró una caché incompleta. El intento posterior con permisos ampliados no se ejecutó inicialmente por un límite temporal de revisión automática; tras restablecerse, la instalación normal terminó correctamente. No se eludió la revisión ni se alteraron dependencias activas.

Se inspeccionó la ventana SEMI en VS Code: no había indicador de archivo sin guardar y Guardar todo estaba deshabilitado. No se guardaron editores ni se interactuó con sus terminales. El commit representa el contenido en disco; Git no captura futuros cambios que permanezcan en un búfer del editor.

## Auditoría del índice

Antes de confirmar, revisar `git diff --cached --stat`, los nombres/tamaños y `git diff --cached --check`. Verificar explícitamente que SQLite, secretos y artefactos no estén en el índice y que las migraciones, pruebas, fixtures, manifests y recursos sí lo estén. La auditoría automatizada de esta preparación revisa patrones de credenciales privadas, URLs de lockfile y reglas de ignore; no sustituye una gestión futura de secretos o autenticación de producción.

Los resultados con hash del commit, contenido final, estado de Git y conservación de datos/servidores se entregan fuera del repositorio. No se escribe el hash del commit dentro de sí mismo.

## Límites conservados

El proyecto continúa en Gate 4, en desarrollo y con control físico deshabilitado. Los datos mock/sintéticos no constituyen mediciones agronómicas reales. No se conectó hardware, no se ejecutaron semillas sobre la SQLite principal ni se reiniciaron/detuvieron servidores activos. Los procesos de prueba son temporales. La evaluación con un agricultor, ensayos físicos, calibración, autenticación de producción e integración real siguen pendientes.
