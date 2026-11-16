# Referencia visual y adaptación Gate 1

Archivo auténtico: [SEMI — Plataforma Web de Monitoreo](https://www.figma.com/design/F2XyQEUnHkjW1cjifhJzlB/SEMI-%E2%80%94-Plataforma-Web-de-Monitoreo).

## Evidencia disponible

En la auditoría anterior se inspeccionó por MCP el inventario de páginas y por vista web el sistema de diseño y cuatro wireframes. `01 — Wireframes` contiene la sección `4:10`; Inicio fue seleccionado como nodo `4:11`. Frames 390 x 844, Inter, controles previstos >=44 px. Páginas `02 — Mobile UI` y `03 — Prototype` consultadas vacías. La guía de Figma dice que las conexiones navegables se configurarían en una fase posterior.

En Gate 1 se intentó nuevamente `get_design_context` de `4:10`, solicitando captura, pero Figma MCP respondió límite del plan Starter. `whoami` confirmó Starter. **No se obtuvo un nuevo contexto de alta fidelidad, ni assets, medidas individuales o propiedades auto-layout.** Se continuó con la referencia visual auténtica ya inspeccionada, conforme a la instrucción del usuario para esta limitación. No se modificó Figma.

## Conservado

- Cuatro pantallas, jerarquía de tarjetas, encabezados, batería, actividad e inferior de navegación.
- Tipografía Inter empaquetada localmente, botones rectangulares y superficies claras con bordes suaves.
- Control direccional en cruz, velocidad baja/media, parada y modo asistido deshabilitado.
- Gráfica temporal, registro de lecturas y lista de componentes/mantenimiento.
- Vocabulario explícito de ejemplos/sin datos, reforzado con banner de demostración.

Tokens de la guía observada y utilizados: background #F5F7F5, surface #FFFFFF, text #24313A, secondary #65727A, agriculture #39855D, border #DCE3DF. La guía reserva color para una fase posterior; Gate 1 incorpora color con moderación en procedencia, radar y avisos.

## Diferencias deliberadas

| Elemento original | Implementación | Motivo |
|---|---|---|
| Placeholder de cámara | Radar polar A1 mock | Cámara no confirmada; cambio expresamente autorizado |
| Temperatura y humedad ambiental en resumen | NPK; ambientales se conservan como no disponibles en Datos | Priorizar sensores seleccionados sin inventar lecturas |
| Inclinación demostrativa | No disponible | IMU no confirmada |
| Cámara disponible en Estado | No confirmada / no disponible | Coherencia con inventario |
| Revisar patas/articulaciones | Revisar orugas, ruedas y fijaciones | Locomoción actual |
| Puerto de carga y carga estimada | Batería mock con procedencia; sin afirmar conector físico | Sistema de batería no identificado |
| Registro simple | Muestras NPK/humedad persistentes y esquema manual | Alcance del Gate 1 |
| Navegación propuesta | Botones navegables y hash de URL | Funcionalidad real del MVP |
| Un frame fijo móvil | Flujo con scroll y reglas tablet/escritorio | Responsive solicitado; no hay diseño desktop verificado |
| Sin herramientas de escenario | Panel plegable y banner | Reproducir fallos y evitar confundir demo con hardware |

## Fidelidad y verificación

No se afirma reproducción 1:1. Se conserva la composición principal; los contenidos adicionales aumentan el alto, hay iconos Lucide equivalentes de uso general y la distribución de escritorio es una adaptación documentada. No se recibieron recursos estáticos descargables del contexto Figma. Espaciados y tamaños individuales se eligieron de forma coherente, pero no se acreditan como extracción exacta.

Se verificaron las cuatro pantallas a 390 px, 768 px y 1440 px en Chromium, con comprobación de scrollWidth y capturas en `evidence/`. Las capturas de página completa pueden mostrar la barra fija a la altura del viewport original; en navegación normal permanece en el borde inferior del teléfono. Comparación por diferencia de píxeles con Figma y validación sobre dispositivo físico quedan pendientes.
