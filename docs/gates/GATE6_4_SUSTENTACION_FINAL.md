# SEMI · Gate 6.4
## Sustentación de teleoperación y medición agrícola

**Fecha:** 18 de noviembre de 2026. **Estado de aceptación física:** pendiente de ensayo presencial. El operador decide cada movimiento. El radar representa distancias en el marco local del sensor. La ubicación de muestreo la aporta una persona.

## Recorrido para la exposición

1. Abrir el perfil operativo. Seleccionar el cafetal en la barra superior o guardar su nombre en «Configurar mi cafetal». Crear sectores y puntos si se conocen. «Salir por ahora» permite abrir Control sin terminar el registro.
2. En Inicio, mostrar la lectura ADC recibida del sensor capacitivo. Nitrógeno y potasio llevan «Simulado» y la explicación «Valor de ejemplo. No tenemos un sensor para medirlo». El parámetro de la URL `?semilla=64` permite repetir los valores. Se conservan en la sesión de la pestaña y el generador vive en React. El contrato visual de nutrientes incluye valor, unidad y origen.
3. En Control, mostrar primero el radar. Con el lector autorizado, una revolución reciente y válida dibuja los puntos. Un puerto detectado por sí solo no identifica al A1M8. Un escaneo vencido desaparece y el error se puede consultar en los detalles.
4. Únicamente después de la revisión y autorización presencial, abrir «Habilitar control supervisado», comprobar el identificador del equipo y habilitar el mecanismo revisado. Mantener pulsada una dirección o Subir/Bajar. Soltar para detener. DETENER ROBOT cancela ambos permisos. El estado de orden activa expresa lo solicitado, sin atribuir una confirmación mecánica a los drivers.
5. En Datos, consultar el historial ADC del cafetal. Elegir un lugar y pulsar «Asociar a …» en la lectura correspondiente. Al seleccionar «Solo el lugar seleccionado» se muestran sus lecturas. Si se desconoce el lugar, conservar «Sin punto asignado». Los valores demostrativos de N y K no se escriben en este historial.

## Integración y configuración

**LiDAR.** Se conserva el lector USB y el canal local de Gate 6.3. El usuario reportó que ya vio puntos físicos en RoboStudio y en SEMI. Este gate no repitió la adquisición física. La selección de COM, identificación, inicio autorizado y cierre corresponden al procedimiento existente. [Procedimiento del lector](LIDAR_PUBLICACION_WINDOWS.md)

**ESP32.** Continuar con el registro, sesión, token y Wi-Fi existentes. Verificar que el backend usa la base correcta antes de registrar otro equipo. El firmware diagnóstico conserva su consulta STOP. El sketch incorpora el canal supervisado solamente cuando su configuración local define `SEMI_MOTOR_KEY`. La configuración de red, NVS y telemetría continúa en el puente anterior. No se distribuyen secretos ni un binario preparado para actuar.

| Ajuste | Dónde | Valor o función |
|---|---|---|
| SEMI_MODE / SEMI_DEVICE_INTEGRATION / SEMI_LIDAR_SOURCE | Django | operational / diagnostic / real |
| SEMI_DEVICE_TOKENS | Django | Mapa existente de ID a token de telemetría |
| SEMI_BENCH_DEVICE | Django | ID exacto de una placa registrada y habilitada |
| SEMI_MOTOR_KEY | Django y semi_config.h local | Clave independiente de alta entropía, al menos 32 caracteres ASCII, para HMAC-SHA256 |
| SEMI_OPERATOR_KEY | Django y operador | Otra clave aleatoria de al menos 32 caracteres. El operador la introduce en Control. No se publica en Vite, URL, almacenamiento del navegador ni respuestas de API |
| SEMI_BENCH_STORE | Django | SQLite de mando separada, predeterminada backend/bench-runtime.sqlite3. Usar disco local del equipo, una ubicación común a los procesos y distinta de la base agrícola. Para banco con OneDrive, elegir explícitamente una ruta local fuera de la sincronización |
| SEMI_TRACTION_VERIFIED / SEMI_RACK_SUPERVISED | semi_config.h local | Macros numéricas independientes, predeterminadas a 0. Poner a 1 solo el mecanismo comprobado para ensayo supervisado |
| SEMI_SAMPLING_POINT_ID | semi_config.h local | 0 omite el punto. Un ID configurado debe pertenecer al cafetal registrado. Los puntos pueden asignarse luego desde Datos |

Usar claves distintas para operador, firma y telemetría. Mantener el navegador en localhost en el PC del banco o servirlo mediante HTTPS al teléfono. El canal HTTP histórico de telemetría presupone Wi-Fi local de confianza. El secreto de firma de órdenes no viaja por HTTP. El dispositivo manda su sesión, identificador aleatorio de arranque/conexión, contador creciente y máscara de drivers revisados. Django verifica credencial, sesión y firma antes de responder a la consulta. La respuesta está firmada y correlacionada con esa consulta. Las peticiones del navegador requieren CSRF y clave de operador. Un perfil sin estas claves conserva el diagnóstico.

La tabla adicional de la migración `devices.0002_manual_reading_location` conserva por separado la decisión del estudiante. En otras instalaciones aplicar `python backend/manage.py migrate` sobre la base prevista y respaldada. Utilizar los comandos de desarrollo existentes para iniciar Django y Vite. Reiniciar los servicios tras modificar su entorno. La adquisición del LiDAR se autoriza aparte.

### Movimiento acotado

| Propiedad | Comportamiento implementado |
|---|---|
| Tracción | TB6612FNG. PWMA 2, AIN1 5, AIN2 4, STBY 15, PWMB 25, BIN1 26, BIN2 27. Adelante y atrás mueven ambos canales en el mismo sentido lógico. En los giros se invierte uno |
| Cremallera | L298N. ENB 18, IN3 19, IN4 21. El sentido real de subida requiere verificación mecánica |
| PWM de banco | 1000 Hz, 8 bits. Baja 80/255, media 120/255 y cremallera 80/255. Son límites iniciales del software, pendientes de medir. Referencias previas 150/255 y 120/255 |
| Plazos | Renovación de intención cada 150 ms. Validez de intención 350 ms. Consulta de placa aproximadamente cada 50 ms más transporte. La placa admite hasta 250 ms contados desde el comienzo de la consulta. Enlace caducado a los 450 ms en el servidor |
| Recorrido continuo | Hasta 1,5 s de tracción y 300 ms de cremallera por pulsación. La renovación conserva el plazo absoluto original. Al agotar el permiso el servidor desarma el dominio |
| Parada local | Tarea FreeRTOS separada de HTTP que revisa Wi-Fi, neutral, inversión y reloj local. El watchdog de tareas de ESP-IDF supervisa esa tarea con plazo de respaldo de 2 s y pánico habilitado. Si no se puede registrar, el transporte de órdenes no arranca. Tras caducar exige neutral. Una respuesta inválida corta ambos mandos y cambia la sesión de enlace. Reinicio con salidas deshabilitadas |
| Parada general | Invalida las dos ventanas de mando y desarma ambos dominios. Una solicitud anterior retrasada queda rechazada. La pérdida completa del canal deja actuar el plazo local. Medir latencia y distancia de parada con el montaje real |
| Disponibilidad | La placa acredita la configuración del driver y su inicialización PWM. TB6612FNG y L298N en este cableado no informan continuidad del motor, giro, posición ni corriente. Una desconexión de cables con la placa encendida requiere detección humana o instrumentación adicional |

La habilitación en Control también permite desactivar únicamente tracción o módulo. Ante un cable de motor suelto, el operador debe desactivar ese mecanismo.

La orden general quita energía de mando a los puentes. La inercia, la carga y la dirección del montaje determinan la distancia recorrida después. Probar la retención mecánica de la cremallera al desenergizarla.

### Sensor y cafetal

El sketch anterior del rover refería GPIO34. El firmware integrado realmente llama a `analogRead(kPin)` con `kPin=35`; se corrigieron los mensajes de arranque y se conservó el pin. El equipo debe trazar el conductor de salida analógica hasta la placa y verificar el pin. Repetir las lecturas con cambios físicos controlados. Un cero se conserva como ADC recibido y se señala para revisión. Una entrada analógica flotante puede producir números: la presencia eléctrica de la sonda se comprueba presencialmente. No se calculan porcentajes.

«Configurar mi cafetal» guarda en SQLite nombre, cultivo de referencia, etapa y finalización, sectores y archivo, puntos con código/nombre y esquema relativo opcional. El cultivo existente es fijo. La asociación del dispositivo determina el cafetal de recepción. El historial de muestras agrícolas de gates anteriores conserva su procedencia. El nuevo historial ADC admite lecturas sin punto, puntos enviados por el firmware y anotaciones manuales del mismo cafetal. Se rechazan asociaciones cruzadas y se conserva íntegro el mensaje del ESP32. El esquema relativo opcional lo introduce el usuario. El LiDAR no genera puntos de muestreo ni coordenadas geográficas.

## Registro de banco para el equipo humano

Completar cada fila con fecha, responsable, instrumento, observación real y resultado. Ante una anomalía, soltar el mando, cortar la alimentación de potencia y dejar ese mecanismo desarmado. Ninguna fila pendiente acredita movimiento o protección física.

| Comprobación | Acción humana y evidencia que se debe registrar | Resultado de este gate / impedimento |
|---|---|---|
| 1. Alimentación | Con potencia cortada revisar esquema y reguladores. Medir fuente y VM, alimentación lógica y alimentación de la sonda. Verificar masa común y señal ADC dentro del rango de la placa | Pendiente. Sin acceso al cableado ni al multímetro |
| 2. Corriente y protección | Comparar corriente nominal, arranque y bloqueo de cada motor con capacidad continua, pulsada y térmica de la placa y cableado. Verificar fusibles y corte físico accesible bajo carga controlada | Pendiente. Sin modelos de motor, corriente medida, selección de fusibles ni prueba del corte |
| 3. Arranque | Motores sin energía, observar con instrumento STBY, ENB y PWM al encender, reiniciar y reconectar. Verificar inhibición externa incluso durante reset y ausencia de jumper ENB que fuerce el L298N. Revisar strapping de GPIO2, 5 y 15 en ESP32 clásico | Pendiente. Sin osciloscopio ni placa inspeccionada |
| 4. Comunicación | Con potencia de motores inhibida verificar ID, sesión, estado periódico y marcas de recepción en Django. Interrumpir Wi-Fi y recuperar. Confirmar que ningún permiso reaparece | Pendiente. Sin sesión física autorizada en este gate |
| 5. LiDAR USB | Identificar puerto actual y revisión. Cerrar RoboStudio. Con lector autorizado comprobar puntos, cambio de distancias y radar reciente. Cerrar lector o retirar cable, observar interrupción y ausencia de puntos antiguos | Éxito físico anterior reportado por el equipo. Sin nueva apertura COM autorizada |
| 6. Sonda capacitiva | Identificar GPIO35/34 por continuidad sin energía. Verificar alimentación y respuesta con dos condiciones de suelo. Registrar ADC, hora y punto. Ante cero persistente verificar salida analógica y pin. Mantener pendiente la calibración | Pendiente. Sin inspección de cable ni mediciones presenciales |
| 7. Tracción | Ruedas elevadas y vehículo asegurado. Habilitar solo tracción. Ensayar adelante, atrás, izquierda y derecha en baja. Medir media, comprobar polaridad, duración, corriente y distancia antes de ponerlo en el suelo | Pendiente. Requiere revisión 1–3 y orden presencial |
| 8. Paradas de tracción | Con área contenida medir respuesta al soltar, cancelar toque, perder foco, cerrar pestaña, cortar red, STOP general, reset y parada física. Registrar tiempo hasta salida inactiva y hasta detención mecánica | Pendiente. Los plazos del código no son mediciones de frenado |
| 9. Cremallera | Sin potencia inspeccionar recorrido, retención de carga, topes y ambos finales. Comprobar eléctricamente corte direccional y comportamiento ante cable roto. Con espacio libre en ambos sentidos, operador junto al corte, habilitar solo recorrido limitado. Verificar subida, bajada, liberación, STOP e interrupción. Medir recorrido por pulso y corriente | Pendiente. Presencia y funcionamiento de finales y protección de sobrecorriente sin confirmar. El software permite únicamente ensayo manual limitado. Un temporizador no acredita el final del recorrido |
| 10. Independencia | Con LiDAR desconectado repetir un pulso autorizado de cada mecanismo. Con un mecanismo desarmado verificar el otro. Repetir con NPK ausente y sin lectura ADC | Pendiente en hardware. Separación comprobada en software |
| 11. Contexto y procedencia | Asociar una lectura real a un punto elegido por el estudiante. Mostrarla en Datos. Recargar Inicio y comprobar que N/K conservan «Simulado» y no figuran como mensajes del ESP32 | Automatizado con datos de prueba. Recorrido con medición física pendiente |

**Alimentación del TB6612FNG.** El máximo absoluto publicado para VM es 15 V. Una fuente de 24 V directa sobre VM excede ese máximo. Seleccionar y medir una alimentación dentro del rango operativo de la ficha y compatible con el motor. La cifra de pico de corriente tiene condiciones de pulso y no es la capacidad continua de la placa. [Ficha Toshiba](https://toshiba.semicon-storage.com/info/datasheet_en_20141001.pdf?did=10660)

Comprobar la placa L298N efectiva, sus diodos, jumper, regulador y disipación. Ambos enables son independientes. Contrastar el arranque con el esquema de la placa ESP32 específica, incluidos los estados de los pines de configuración antes de que se ejecute el sketch. [L298 de ST](https://www.st.com/en/motor-drivers/l298.html) · [Guía de diseño ESP32](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32/schematic-checklist.html) · [LEDC de Arduino-ESP32](https://docs.espressif.com/projects/arduino-esp32/en/latest/api/ledc.html)



## Verificación de software y datos conservados

| Verificación | Resultado y alcance |
|---|---|
| Django | 143 pruebas aprobadas con base aislada. Incluyen firma del dispositivo, CSRF y clave del operador, dominios independientes, orden retrasada tras STOP, cambio de arranque, contradicción, tope de pulso y conservación de telemetría al asignar un punto |
| Esquema Django | `check` sin incidencias y `makemigrations --check --dry-run` sin cambios pendientes de generar |
| React y Vite | Comprobación TypeScript y compilación de producción aprobadas |
| Playwright | 84 casos aprobados en las suites configuradas. 29 de regresión general, 21 de actuadores, 10 de fuentes, 11 del perfil operativo, 12 de dispositivo/datos y 1 del circuito de mando firmado. Los reintentos no se suman al total |
| Firmware para placa | Dos compilaciones para `esp32:esp32:esp32`, core Arduino-ESP32 3.0.7, distribución oficial 3.0.7-cn, y ArduinoJson 7.4.2. Banco con ambos drivers compilados: 1 005 553 bytes de programa. Diagnóstico: 977 129 bytes. Configuración temporal sin credenciales del equipo |
| Supervisores C++ | Tres programas aprobados con aserciones activas: supervisor previo, independencia de dominios y guardia del firmware de banco (caducidad, límite absoluto, inversión, enlace y desbordamiento del reloj). Se compilaron los ejecutables Windows, pero Control de aplicaciones bloqueó su ejecución. La verificación ejecutada fue en WebAssembly/WASI aislado con Zig 0.13, sin optimización y sin acceso a dispositivos. Los tiempos del reloj de ensayo no miden frenado físico |
| Capturas | Cuatro pantallas en el perfil operativo con telemetría de prueba, marcadas «PRUEBA DE INTERFAZ · SIN HARDWARE». El radar de esta captura está sin lecturas. Las imágenes no acreditan conexión física |
| Base existente | Antes del cambio, la base `backend/demo.sqlite3` de esta ruta tenía cero cafetales, puntos, muestras, dispositivos y mensajes. Se hizo una copia y se aplicó únicamente la tabla de asociación manual. La comparación de filas previas en 17 tablas coincidió. `quick_check` y claves foráneas correctas. Sin sembrar ejemplos en la base del usuario |
| Equipo y repositorio | Sin apertura COM, flasheo, pruebas físicas de motores, cambios de credenciales, commit ni push durante este gate |

La prueba de mando enlaza eventos de teclado en React con Django y un cliente ESP32 de prueba que verifica las firmas. Comprueba avance en velocidad media, liberación, subida y STOP general. Las pruebas de los gates anteriores conservan las comprobaciones de gesto, foco y pérdida de conexión. En las primeras corridas de regresión se observaron carreras de arranque de CSRF y de actualización del bloqueo simulado. La preparación de la prueba obtiene el token antes de abrir la página y el botón refleja el bloqueo hasta que el estado se actualiza. Las ejecuciones fallidas no cuentan como aprobaciones.

### Capturas para revisar

[Inicio con ADC y ejemplos N/K](../evidence-gate6_4/inicio.png) · [Control manual](../evidence-gate6_4/control.png) · [Estado del robot](../evidence-gate6_4/estado.png) · [Datos del cafetal](../evidence-gate6_4/datos.png)

### Reproducción en desarrollo

Desde la raíz de SEMI, con las dependencias de desarrollo instaladas, ejecutar las suites de navegador de forma secuencial porque los perfiles anteriores comparten su base E2E. Los comandos siguientes no cargan firmware ni inician el lector físico.

```powershell
.\.venv\Scripts\python.exe backend/manage.py test apps.agriculture apps.devices apps.lidar
.\.venv\Scripts\python.exe backend/manage.py check
.\.venv\Scripts\python.exe backend/manage.py makemigrations --check --dry-run
npm --prefix frontend run build
npm --prefix frontend run test:e2e
npm --prefix frontend run test:actuators
npm --prefix frontend run test:sources
npm --prefix frontend run test:mvp
npm --prefix frontend run test:device
npm --prefix frontend run test:bench
```

Para repetir la compilación sin equipo conectado, elegir el ESP32 clásico y ejecutar `arduino-cli compile --fqbn esp32:esp32:esp32 firmware/semi_diagnostic/SEMI_Diagnostic` con una copia privada de la configuración. No se necesita puerto para compilar. La versión y variante de la placa instalada en el robot deben verificarse en el banco.
