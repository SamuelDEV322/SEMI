> Actualización 2026-11-16: el perfil predeterminado es operativo, sin fuentes sintéticas ni cambio de origen desde UI/API. Consultar [OPERATING_PROFILE.md](OPERATING_PROFILE.md) para el contrato vigente y los límites físicos. Las secciones de Gates anteriores conservan su contexto histórico.

> Actualización Gate 2: consultar [GATE2.md](GATE2.md). El contenido Gate 1 se conserva como antecedente.

# Arquitectura — Gate 1

## Decisión

El usuario seleccionó Django, SQLite, React, TypeScript, Vite y Tailwind para esta implementación. Esta decisión reemplaza la propuesta provisional anterior de un frontend sin persistencia de servidor. Se mantiene la operación en LAN sin dependencia de nube.

```text
Navegador React
    | HTTP JSON, mismo origen /api mediante proxy de Vite
Django REST Framework
    |-- agricultura: muestras -> SQLite
    |-- telemetría: eventos relevantes -> SQLite
    |-- registro de proveedores -> mocks en memoria
            |-- MockRobotProvider
            |-- MockTelemetryProvider
            |-- MockNPKProvider
            `-- MockLidarProvider
```

Frontend: componentes compartidos, cuatro páginas, servicio HTTP tipado y hooks de polling/control. Los valores agronómicos y escaneos proceden de Django; no se dispersan fixtures de medición por las páginas. Los textos de hardware no confirmado sí son contenido estático explícito.

Backend: un modelo `Sample` agrupa N, P, K y humedad de un mismo contacto y conserva campos ausentes como null. Evita duplicar una muestra agronómica y otra NPK con identidades divergentes. `SystemEvent` persiste capturas, escenarios y cambios de dirección; no registra cada renovación ni cada punto LiDAR.

## Transporte

Gate 1 usa HTTP, no WebSockets. Polling: estado 500 ms; escaneo 1000 ms; última muestra 2500 ms; historial 5000 ms. Son parámetros de demostración, no garantías de latencia del robot. Cada operación HTTP tiene timeout de 3500 ms y los errores se hacen visibles. No se reenvían comandos de movimiento tras un fallo.

La interfaz renueva movimiento aproximadamente cada 150 ms mientras hay pulsación. Evita envíos concurrentes de renovación. El simulador limita la vigencia a 450 ms y al vencimiento de una ventana de 1500 ms emitida por él; valida secuencia, época y operador. STOP invalida la época y ventanas anteriores. Una reconexión no reproduce órdenes. El simulador evalúa caducidad al recibir una consulta o un comando; no ejecuta un lazo de tiempo real.

Estos mecanismos permiten probar comportamiento lógico y paquetes atrasados. Un firmware futuro necesita reloj monotónico, supervisor propio, estado de arranque inhibido y protección física independiente. Un ACK simulado no acredita inmovilidad física.

## Interfaces y futuro

`adapters/contracts.py` define Protocols `RobotProvider`, `TelemetryProvider`, `NPKProvider`, `LidarProvider` y TypedDict del escaneo. Gate 1 solo instancia mocks en `adapters/registry.py`.

Integraciones planificadas, sin clases vacías ni código ejecutable:

| Adaptador futuro | Entrada / responsabilidad | Condición previa |
|---|---|---|
| Esp32RobotProvider | Enlace de estado y comandos con ESP32 | Modelo, firmware y seguridad validados |
| RealNPKProvider | Lectura del sensor y protocolo real | Modelo, alimentación, unidades y calibración |
| WirelessLidarProvider | Mensajes desde un puente Wi-Fi | Contrato y rendimiento eléctrico/temporal verificados |
| SerialLidarProvider | Kit USB A1 y SDK/protocolo oficial | Puerto elegido expresamente por operador |

Preferencia futura: A1 -> interfaz compatible -> puente Wi-Fi -> Django. Respaldo: A1 -> kit USB -> computador -> Django. Ambos deben producir el mismo contrato `Scan`. El A1 no produce coordenadas globales por sí mismo.

Configuración reservada: `SEMI_FUTURE_LIDAR_TRANSPORT`, `SEMI_FUTURE_LIDAR_PORT`, `SEMI_FUTURE_LIDAR_URL`. Son metadatos de planificación: ningún componente las utiliza para abrir dispositivos o sockets. `SEMI_PROVIDER` distinto de mock provoca un error de configuración.

## Operación, seguridad y alcance

- Un proceso Django con estado volátil protegido por RLock. SQLite conserva datos al reiniciar.
- Sin Docker, Channels, broker, Redis, Celery, nube ni persistencia continua LiDAR.
- Tokens CSRF y comprobación de origen en escrituras, incluidas peticiones anónimas DRF.
- Sin autenticación de usuarios en Gate 1. El identificador de sesión arbitra simulación; no es una credencial.
- Servidores ligados a loopback por defecto; LAN se habilita manualmente. No es una instalación para exposición pública.
- Fuentes Inter empaquetadas localmente; no hay mapas externos, CDN ni fuentes remotas durante la operación.
- No SLAM, cámara, odometría, localización, planificación o evitación automática.

Referencias consultadas: [Django 5.2](https://docs.djangoproject.com/en/5.2/), [DRF](https://www.django-rest-framework.org/), [Tailwind con Vite](https://tailwindcss.com/docs/installation/using-vite), [Vite](https://vite.dev/guide/), [SDK oficial SLAMTEC](https://github.com/Slamtec/rplidar_sdk).


## Evolución Gate 3

Ver GATE3.md para el asistente de instalación, contexto por Plot, separación de puntos/zonas/lecturas y simulador por recorrido. CropProfile y OnboardingState se representan como campos de Plot; no se añaden servicios. La superficie registrada es metadato manual; la superficie del ensayo es simulada. Ninguna autoriza movimiento físico.


## Evolución Gate 4

Ver GATE4.md. Sectores descriptivos (TerrainZone por compatibilidad), archivo seguro y SectorMembership con referencias protegidas. SurfaceTrial separa el estado de laboratorio de la configuración agrícola. Installation coordina cuatro etapas y reutiliza SectorManager, PointEditor y RelativeMap en Datos. Se conserva polling HTTP, SQLite y los adaptadores anteriores; no se añaden servicios ni dependencias.
