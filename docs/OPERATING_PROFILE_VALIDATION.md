# Validación del perfil operativo — 16/11/2026

Solicitud: retirar fuentes/ensayos de la interfaz habitual, seleccionar adquisición real desde configuración y preparar pruebas asíncronas del equipo.

## Resultado funcional

- Perfil predeterminado operativo, LiDAR real y herramientas de desarrollo deshabilitadas.
- Selector de fuente eliminado del frontend en todos los perfiles; la antigua operación API responde 405.
- Onboarding conserva cafetal/sectores/lugares; no ofrece capturas sintéticas en operación.
- No se inventan batería, conexión ni STOP físico. Mandos y captura permanecen indisponibles hasta integrar ESP32/sonda.
- El lector A1 USB existente publica escaneos al servidor, con inicio deliberado; la web nunca abre puertos. Validación reforzada de procedencia, números, reloj y caducidad.
- Datos mock/replay conservados para regresión interna, sin sustitución automática en operación.
- Favicon SVG incluido. No se introdujo unsafe-eval para resolver un error de extensión del navegador.

## Ejecuciones finales

| Comprobación | Resultado |
|---|---|
| Django check | Sin incidencias |
| makemigrations --check --dry-run | Sin cambios pendientes |
| Migración agriculture 0007 | Aplicada correctamente |
| Django agriculture + lidar | 60 pruebas aprobadas |
| Navegador, perfil operativo | 11 pruebas aprobadas, 18.1 s |
| Regresión de Gates 2/4, perfil de desarrollo explícito | 29 pruebas aprobadas, 1 min |
| TypeScript + Vite build | Correcta |
| Black --check | 47 archivos sin cambios de formato |
| git diff --check | Correcto |
| Inspección del contenido propuesto | Sin SQLite, secretos, venv, logs, entregas ni evidencias generadas |

El navegador comprobó 360, 390, 768 y 1440 px, ambos temas, mandos de al menos 44 px, ausencia de desbordamiento horizontal y Control completo sin scroll. La regresión también cubre 740x360, táctil, teclado, cancelación, pérdida de foco/conexión, historial, sectores y STOP lógico en el ensayo de superficies.

En las primeras ejecuciones se corrigieron un selector de texto de la prueba y el token CSRF que faltaba en otra petición de prueba. Los resultados de la tabla corresponden a las ejecuciones finales, no a las fallidas.

## SQLite y continuidad

Backup consistente previo conservado fuera de Git. Se comparó el contenido completo de cada tabla de aplicación antes/después de migrar: todas las filas existentes permanecen idénticas. Se mantienen 17 muestras, 9 lugares, 3 terrenos, 4 sectores y 86 eventos, además de las relaciones y estados anteriores. integrity_check=ok y foreign_key_check sin errores. No se ejecutaron semillas en la base habitual. Las semillas/flush de Playwright se limitaron a e2e.sqlite3.

La migración 0007 reemplaza la restricción mock-only por una lista de procedencias conocidas; no cambia los valores históricos. Las filas antiguas no se declaran reales. La SQLite local no forma parte del commit.

El servidor de desarrollo existente en 8000 recargó el código y devolvió mode=operational, dev_tools=false, lidar_source=real y physical_control=false. Vite existente en 5173 encaminó correctamente /api. No fue necesario reemplazar procesos habituales. Los servidores temporales de las pruebas se cierran al terminar.

## Límites de lo comprobado

No hubo un RPLidar físico conectado en esta ejecución. El parser, estados y adquisición se verificaron con fixtures y transporte falso. La prueba de representación de una trama real es un fixture de contrato dentro de Playwright, nunca una lectura persistida ni una prueba física. Las capturas entregadas muestran el estado honesto sin sensor.

No se abrió ningún puerto USB, no se ejecutó lidar_usb ni se energizaron motores. El motor de rotación del sensor requiere inicio deliberado en la prueba del compañero. La implementación no proporciona conducción física, lectura real NPK ni clasificación de materiales. El supervisor aislado de firmware se conserva sin cambios; no se volvió a compilar ni constituye seguridad física validada.

Las pruebas automatizadas no demuestran usabilidad con un agricultor ni comportamiento mecánico. El enlace ESP32 y el modelo/protocolo de sonda siguen pendientes. Ver OPERATING_PROFILE.md para instrucciones y prioridades.

## Evidencias locales

Capturas claro/oscuro de Inicio, Datos, Estado y Control en docs/evidence/operational; logs finales en docs/repository-checks. Son artefactos locales ignorados. Una copia de la guía y capturas queda en outputs del workspace para compartirlas; no se publican bases ni logs personales en GitHub.
