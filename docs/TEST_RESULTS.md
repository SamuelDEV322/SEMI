# Resultados de validación — Gate 1

Fecha de trabajo: 15 de noviembre de 2026, America/Bogota. Pruebas de software en Windows; **ningún ensayo físico**.

## Resultado final

| Comprobación ejecutada | Resultado | Evidencia |
|---|---|---|
| Django check | Sin incidencias | evidence/django-check.txt |
| Migraciones iniciales | Aplicadas a SQLite; el runner crea también la base de prueba | Migraciones versionadas y backend-tests.txt |
| makemigrations --check --dry-run | No changes detected | evidence/migrations-check.txt |
| Tests Django/DRF | **23/23 aprobadas** | evidence/backend-tests.txt |
| pip check | No broken requirements found | evidence/pip-check.txt |
| tsc -b y Vite build | Correctos | evidence/frontend-build.txt |
| Chromium E2E | **8/8 aprobadas**, ejecución final 9,8 s | evidence/browser-tests.txt |
| Navegación / responsive | Cuatro vistas a 390, 768 y 1440 px, sin desbordamiento horizontal | 12 capturas PNG en evidence/ |
| Código formateado | Prettier y Black aplicados | Archivos fuente |
| Git | Inicializado únicamente en SEMI, sin commits | Repositorio local |

Bundle de JS: aproximadamente 252 kB sin comprimir / 80 kB gzip. CSS: aproximadamente 19 kB / 5 kB gzip. Fuentes Inter latinas empaquetadas; no CDN en operación.

## Cobertura backend

Endpoints de consulta y procedencia demo; base vacía; seed repetible; captura persistente; null frente a cero; rechazo de datos reales, unidades incompatibles, números no finitos y posiciones incorrectas; CSRF; rechazo de modo físico y campos extra; control diferencial simulado; secuencias repetidas; operador exclusivo; ventanas caducadas; caducidad sin STOP del navegador; STOP invalida paquetes previos; desconexión/reconexión sin reanudar; escenarios no_data/error; contrato LiDAR y obsolescencia; límites del historial; arranque rechazado con proveedor real.

## Cobertura navegador

1. Cuatro pantallas a 390 x 844.
2. Cuatro pantallas a 768 x 900.
3. Cuatro pantallas a 1440 x 900.
4. Registro de muestra en Django/SQLite, consulta tras recargar, parcela etiquetada y radar visible.
5. Mouse mantenido, liberación, teclado y pérdida de foco.
6. Sin datos, obsolescencia, desconexión simulada y error de adquisición.
7. Touch sostenido y touchCancel mediante entrada táctil emulada de Chromium; sin errores JavaScript.
8. Estado cargando, pérdida real de acceso a red desde el contexto del navegador, controles deshabilitados y recuperación.

Las pruebas E2E usan servidores Django/Vite reales locales. No sustituyen la API con fixtures del navegador. El escenario de fallo es proporcionado por el backend; la prueba offline corta además la red del contexto del navegador.

## Incidencias encontradas y resueltas

- La primera prueba CSRF detectó que la exención de DRF dejaba pasar una escritura anónima. Se incorporó un middleware que aplica la comprobación estándar de Django a todas las escrituras API. La prueba final confirma HTTP 403 sin token.
- Las primeras ejecuciones del navegador no alcanzaban los servidores aislados por el entorno restringido. Se ejecutaron ambos servidores y el navegador en el mismo contexto local autorizado. No se cambió la aplicación para eludir el problema.
- La prueba táctil sostenida inicial apuntaba a un control bajo la navegación fija porque solo verificaba intersección con viewport. Se centró el objetivo antes de enviar touchStart/touchCancel. La prueba final confirma movimiento y parada simulados.
- Se validan unidades para impedir que la API reciba un número y lo reetiquete silenciosamente con otra unidad.

## Limitaciones verificables

- Solo Chromium; no Safari, Firefox ni teléfono físico.
- La emulación responsive no acredita cobertura Wi-Fi rural ni rendimiento del ESP32.
- No existe comparación por diferencia de píxeles contra Figma: MCP estaba limitado por la cuota Starter. FIGMA_AUDIT.md describe la referencia inspeccionada y las diferencias.
- El simulador no es un supervisor de seguridad de tiempo real; la caducidad se evalúa al observar/comandar su estado.
- No se verificaron sensores, calibración agronómica, batería, IP65, pendientes, autonomía ni frenado.
- Las marcas de mantenimiento no son persistentes; el historial de muestras sí lo es.
- No se implementó autenticación de operadores ni despliegue de producción. Loopback es el valor por defecto.
- El historial devuelve hasta 200 muestras por consulta; la UI muestra las 100 recientes. No hay paginación completa.
- Fuentes serial/inalámbrica y todo movimiento físico permanecen pendientes.

No se accionaron motores ni se abrieron puertos seriales/USB. No se avanzó al Gate 2.
