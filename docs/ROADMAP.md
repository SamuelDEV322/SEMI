> Actualización Gate 2: consultar [GATE2.md](GATE2.md). El contenido Gate 1 se conserva como antecedente.

# Roadmap y límites

## Gate 1

Software local ejecutable, cuatro vistas y API Django, SQLite, NPK persistente, esquema manual, radar mock y control exclusivamente simulado. Véase TEST_RESULTS.md para evidencia ejecutada, sin confundir pruebas de software con validación física.

Trazabilidad inicial:

| Requisito | Implementación | Evidencia |
|---|---|---|
| DEMO-01 procedencia visible | Sobre API, banner y source mock | Backend y E2E |
| AGR-01 muestras persistentes | Sample, migración y API | Captura/consulta/recarga E2E |
| AGR-02 posición honesta | none/manual_schematic y parcela etiquetada | Validación de coordenadas y E2E |
| LID-01 percepción básica | Scan, MockLidarProvider y radar | Contrato de 120 puntos y vista |
| CTRL-01 mantener/liberar | Hook manual y comandos simulados | Mouse, teclado, blur y táctil |
| CTRL-02 prohibir movimiento real | Arranque mock-only, rechazo modo físico | Pruebas de configuración y endpoint |
| FAIL-01 comunicación/sensores | Escenarios y timeout HTTP | Desconexión, no_data, stale, error y API offline |
| UI-01 cuatro vistas responsive | Páginas y navegación | 390/768/1440 sin overflow |

## Gate 2 recomendado — adquisición real de solo lectura

Incremento: integrar **una única fuente real del A1**, sin control físico de motores. Primero captura/reproducción de mensajes para fijar contrato y rendimiento. Evaluar el puente inalámbrico deseado con modelo, alimentación y capacidad identificados. Mantener el kit USB como respaldo explícito.

Aceptación propuesta:

1. Identificación, alimentación e interfaz verificadas por el equipo.
2. Adaptador real elegido manualmente; nunca apertura automática de serial.
3. Escaneo con source=real, tiempo de adquisición, validez y calidad del dispositivo.
4. Desconexión, timeout, datos corruptos y obsolescencia visibles.
5. Medición de tasa, CPU y latencia, sin afirmar SLAM/localización.
6. Fuentes mock y real separadas; sin insertar datos simulados como reales.
7. Módulo de motores permanece ausente/bloqueado.

Si no existe un puente Wi-Fi validado, desarrollar primero el adaptador USB de solo lectura con el SDK oficial, conservando la interfaz común. No adquirir hardware ni conectar dispositivos sin autorización aplicable.

## Gates posteriores

- Sondas reales y calibración, procedimiento de contacto y unidades verificadas.
- Posicionamiento validado antes de mapas georreferenciados.
- Autenticación y despliegue local mantenible antes de operación compartida.
- Firmware y protección física, revisión eléctrica y autorización antes de motores.

No se implementó Gate 2 ni navegación autónoma. La preferencia inalámbrica se mantiene como hipótesis de integración, no como capacidad implementada.


## Gate 3 entregado

Asistente persistente, demo aislada y ensayo de superficie exclusivamente simulado, con regresión de interfaz/datos/seguridad. Ver GATE3.md. Próximo incremento recomendado: evaluación con un agricultor, medidas de maqueta y ensayo independiente de detección de materiales, sin motores. No se avanzó automáticamente.


## Gate 4 entregado

Onboarding de cuatro etapas, sectores opcionales administrables, puntos sin posición y Datos por lugar. Historia preservada y ensayo de superficies separado. Próxima validación: observar a un agricultor completar el recorrido sin ayuda, registrar dudas y ajustar; posteriormente estudiar detección independiente de materiales sin actuadores. No se inició Gate 5. Ver GATE4.md y sus limitaciones.
