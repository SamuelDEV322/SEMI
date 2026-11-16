> Actualización 2026-11-16: el perfil predeterminado es operativo, sin fuentes sintéticas ni cambio de origen desde UI/API. Consultar [OPERATING_PROFILE.md](OPERATING_PROFILE.md) para el contrato vigente y los límites físicos. Las secciones de Gates anteriores conservan su contexto histórico.

> Actualización Gate 2: consultar [GATE2.md](GATE2.md). El contenido Gate 1 se conserva como antecedente.

# Estado del hardware

Actualizado para Gate 1 según las especificaciones del equipo. No se efectuó prueba eléctrica ni física.

| Subsistema | Conocimiento actual | Integración en esta aplicación |
|---|---|---|
| Chasis y tracción | Vehículo de orugas dobles; no hexápodo | Solo simulación diferencial |
| Control principal | Familia ESP32; variante pendiente | No conectado |
| LiDAR | **SLAMTEC RPLidar A1 confirmado por el equipo en la solicitud Gate 1** | Mock, 120 puntos por escaneo; sin lectura del A1 |
| Puente Wi-Fi LiDAR | Deseado, sin validación | No implementado |
| Kit USB A1 | Alternativa de respaldo | No se abre ningún puerto |
| Humedad del suelo | Sensor seleccionado; modelo pendiente | Datos mock |
| NPK | Sensor seleccionado; modelo/protocolo/unidades/precisión pendientes | Datos mock, mg/kg solo demostrativos |
| Batería | Aproximadamente 24 V; química/capacidad/BMS pendientes | 72 % simulado; sin medición física |
| Motores/driver | Cantidad, referencias, corrientes y driver instalado pendientes | Ninguna salida física |
| Cámara | No confirmada | No disponible |
| Temperatura/humedad ambiental | Sensores no confirmados | null / no disponible |
| Inclinación | IMU no confirmada | null / no disponible |
| Posición | Sin GNSS, odometría ni SLAM confirmados | Etiquetas y coordenadas esquemáticas manuales |

## Cambio respecto de la auditoría

El modelo LiDAR deja de ser una incógnita: ahora se identifica como A1 por declaración actual del equipo. Esto no confirma alimentación, firmware, funcionamiento ni capacidad de procesamiento del ESP32. La identificación del modelo no se deriva de la fotografía.

## Bloqueo de motores

No asumir compatibilidad de batería de aproximadamente 24 V con TB6612FNG. La hoja de datos establece VM de operación hasta 13,5 V y máximo absoluto de 15 V. La corriente de pico no equivale a corriente continua admisible. [Toshiba](https://toshiba.semicon-storage.com/info/docget.jsp?did=10660&prodName=TB6612FNG).

Antes de integrar movimiento: modelo de cada motor y driver, tensión máxima de batería cargada, corrientes nominales y de arranque/bloqueo, reguladores, protecciones, cableado, parada física, frenado y retención sin alimentación. Requiere validación y autorización explícita en otro gate.

## Datos requeridos al equipo

1. Referencias y fotos legibles de placas, driver, motores, batería y reguladores.
2. Esquema actual y resultados eléctricos ya obtenidos, sin solicitar energización nueva.
3. A1: kit/cableado disponible, alimentación y puente Wi-Fi propuesto.
4. Sondas: fabricante, protocolo, registros, unidades, calibración y procedimiento de contacto con suelo.
5. Firmware existente y pruebas documentadas.
6. Red y teléfonos objetivo, alcance de operación y disponibilidad de computador local.
7. Método futuro de posición; sin esa evidencia no se generarán mapas georreferenciados.

Masa, pendiente, autonomía, IP65 y tiempo de lectura siguen siendo objetivos pendientes de validación.


## Gate 3: maqueta de tierra y arena

No se conectó ni activó ningún dispositivo. El A1 continúa como medición relativa de distancias; no se validó clasificación de tierra/arena. Las categorías del terreno son manuales y el estado del ensayo es simulado. Dimensiones, método de clasificación, posición del sensor y procedimiento de sonda pendientes. Ver bloqueos de movimiento y validación agronómica en GATE3.md.


## Gate 4

Sectores y posiciones esquemáticas son organización manual; no clasifican materiales ni habilitan locomoción. El ensayo de arena se separó en SurfaceTrial. No se abrió USB/serial ni se activaron actuadores. Clasificación real de materiales, NPK/calibración y seguridad física pendientes. El A1 sigue siendo un sensor de distancias sin localización ni reconocimiento de suelo validados.
