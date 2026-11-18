# Corrección localizada: publicación LiDAR en Windows

## Hallazgos comprobados

La excepción reportada ocurre en el reemplazo del archivo local, no constituye evidencia de fallo USB, protocolo LiDAR o firmware ESP32.

En la copia inspeccionada no existen actualmente `backend/runtime`, `lidar-latest.json` ni `lidar-latest.tmp`. Por ello no fue posible consultar las ACL o ReadOnly de los archivos originales ni identificar su propietario de handles. La consulta de procesos por CIM no estuvo disponible con los permisos de esta sesión; no se elevó a administrador, no se instalaron herramientas ni se detuvieron procesos. No se leyó configuración privada para adivinar otra ruta.

El código previo usaba `Path.write_text`, que ya cierra el temporal antes de `Path.replace`: **no se comprobó un handle propio sin cerrar como causa original**. Sí se comprobaron dos defectos: temporal fijo susceptible a colisiones y manejo que volvía a publicar desde except y finally después de un fallo de publicación, provocando excepciones secundarias y ocultando el contexto.

Se reprodujo **WinError 5 nativo de Windows** en un directorio desechable, con un hilo leyendo continuamente el destino mientras otro lo reemplazaba. También se probaron handles Win32 explícitos sin permiso de compartir eliminación, su liberación y un destino ReadOnly. Esto demuestra mecanismos de contención/permisos compatibles con el fallo, **no identifica el origen exacto en el computador de la prueba física**. Un lector que no comparta eliminación, antivirus/indexador, ACL o ReadOnly del archivo original siguen siendo hipótesis a comprobar allí.

Microsoft documenta que los handles deben compartir acceso de eliminación para permitir renombrado/eliminación, y que las ACL controlan derechos específicos del archivo/directorio: [CreateFileW y FILE_SHARE_DELETE](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew), [seguridad de archivos](https://learn.microsoft.com/en-us/windows/win32/fileio/file-security-and-access-rights).

## Corrección

- `adapters/lidar_ipc.py`: `publish_atomic` crea un temporal único por operación con PID y sufijo aleatorio, en el directorio del destino. Serializa JSON válido y sale del contexto del archivo **antes** de invocar `os.replace`, manteniendo reemplazo atómico en el mismo volumen. No trunca, elimina ni reescribe el JSON destino como alternativa.
- Hasta **5 intentos**, con esperas de 10, 20, 40 y 80 ms: 150 ms de backoff total, más la duración de las operaciones del sistema. Solo se reintentan errores Windows 5, 32 y 33 de acceso/compartición/bloqueo. WinError 5 puede ser permanente; los reintentos no suponen que sea transitorio y se detienen al agotar el presupuesto.
- Un destino con atributo ReadOnly comprobado falla inmediatamente. Otros errores de escritura/serialización o códigos distintos no se reintentan. No se modifican ACL, atributos ni permisos para forzar la publicación.
- Se retira únicamente el temporal creado por esa operación. No se borra un temporal antiguo de usuario ni el destino. Un fallo al limpiar el temporal se informa y no se presenta como publicación exitosa.
- `lidar_usb.py`: una `PublicationError` produce un `CommandError` claro, cierra el lector y **omite toda publicación adicional** desde manejador/finalización. No hay llamada recursiva ni recuperación con datos ficticios.
- Para un fallo del sensor ajeno a publicación, se permite una única publicación terminal; si falla, se conserva el error original y se informa también el fallo del disco. Para una salida normal, fallar al publicar el cierre se reporta, sin nuevos intentos a nivel del comando.
- El bloqueo de publicador de Gate 6.3 se conserva durante toda la adquisición. Un segundo publicador es rechazado; los temporales únicos no sustituyen ese bloqueo.

La última instantánea válida permanece intacta. Si no recibe reemplazos, los plazos existentes de escaneo/heartbeat la marcan obsoleta o interrumpida. Ningún éxito se confirma por escribir solo el temporal. No se modifican contratos de frames ni endpoints.

## Pruebas ejecutadas, sin hardware

Línea base: **25 pruebas LiDAR OK**. Resultado final: **35 pruebas LiDAR OK**, incluidas diez nuevas, y **137 pruebas Django OK** en la regresión completa (agriculture, lidar, devices). Ninguna prueba omitida en esta ejecución Windows. `git diff --check` sin incidencias.

Las pruebas nuevas verifican:

1. WinError 5/32/33 transitorio, temporal cerrado comprobado mediante apertura exclusiva Win32 y nombres únicos entre operaciones.
2. Error de acceso permanente: cinco intentos, cuatro esperas, destino idéntico y temporales propios retirados.
3. Errores no transitorios y JSON inválido sin reintentos ni publicación.
4. ReadOnly real sobre archivo desechable: rechazo inmediato y atributo preservado.
5. Handle Win32 sin FILE_SHARE_DELETE: primer reemplazo falla, liberarlo permite el siguiente intento.
6. Contención Win32 permanente: error acotado, último JSON intacto.
7. Segundo hilo publicador rechazado por el bloqueo existente.
8. Lectores concurrentes observan solo JSON completos. Si su contención agota los reintentos, se verifica preservación byte por byte; después de cerrar lectores la publicación vuelve a funcionar. La primera ejecución de este caso reprodujo WinError 5: exigir éxito incondicional bajo contención permanente habría contradicho el límite de reintentos.
9. Fallo al publicar arranque, captura o cierre: sin publicaciones secundarias, lector cerrado y error explícito.
10. Error de sensor no ocultado por un fallo posterior de publicación terminal.

El test end-to-end lector ficticio → JSON → API de Gate 6.3 se actualizó para observar `os.replace` en lugar de `Path.replace`; conserva sus aserciones de procedencia, puntos y cierre.

Comandos desde SEMI:

```powershell
.\.venv\Scripts\python.exe backend\manage.py test apps.lidar
.\.venv\Scripts\python.exe backend\manage.py test apps.agriculture apps.lidar apps.devices
git diff --check
```

Logs y diff completos locales: `docs/repository-checks/lidar-publication.log`, `lidar-publication-regression.log`, `lidar-publication.patch`. Las pruebas de ACL/handles se realizan únicamente con archivos desechables creados por los tests, nunca sobre el spool del usuario.

En una repetición de la regresión apareció un fallo intermitente previo y ajeno a publicación: `DeviceTests.test_adc_persistence_original_values_time_source_and_no_fake_npk` exige measured_at < received_at, pero ambos timestamps fueron idénticos en Windows. No se modificó esa prueba ni el servicio de telemetría, por estar fuera del alcance. Se conserva la ejecución en `lidar-publication-clock-race.log`; las pruebas LiDAR pasaron también en esa ejecución. Este resultado no se oculta ni se atribuye al cambio de publicación.

## Archivos y conservación

Modificados: `backend/adapters/lidar_ipc.py`, `backend/apps/agriculture/management/commands/lidar_usb.py` y `backend/apps/lidar/test_gate6_3.py`. Nuevo: `backend/apps/lidar/test_publication.py`. Este informe documenta la corrección. Sin cambios de frontend, firmware, broker STOP-only, configuración privada, modelos o migraciones. Las pruebas Django utilizan bases aisladas; no se ejecutaron semillas sobre SQLite del usuario. No se abrió COM ni se inició adquisición física. Sin commit ni push.

## Comprobación pendiente en el equipo del incidente

Sin iniciar el lector ni abrir COM: consultar `Get-Item` (Attributes/ReadOnly) y `Get-Acl` del directorio y del JSON real usados por esa instancia. Contrastar identidad del proceso y ruta efectiva. Si existe una herramienta de inspección de handles ya autorizada, identificar los procesos que mantienen abierto ese archivo y sus modos de compartición; no cerrar handles ni detener procesos indiscriminadamente. No cambiar permisos globales ni recomendar administrador como solución.

Si con la corrección se agota el presupuesto, conservar el mensaje completo y comprobar ACL/ReadOnly/contención en ese equipo. El error persistente es un fallo de publicación que requiere diagnóstico, no autorización para ocultarlo, reescribir el destino de forma no atómica o atribuirlo al USB.
