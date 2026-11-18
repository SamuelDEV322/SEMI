// ==========================================
// SEMI - Gate 6
// ESP32 Diagnostic Firmware
// Universidad - Prototipo agrícola
// ==========================================
//
// Integración:
// - Sensor capacitivo ADC1
// - Comunicación Wi-Fi
// - API Django Gate 5
// - Persistencia de secuencias
// - Telemetría y heartbeat
//
// El perfil por defecto conserva el diagnóstico. El banco supervisado requiere
// claves y habilitación independiente por mecanismo en la configuración local.

#include <Arduino.h>

#include "semi_config.h"
#include "SemiApiBridge.h"
#ifdef SEMI_MOTOR_KEY
#include "SemiBench.h"
#else
#include "SemiMotorAdapter.h"
#endif
#include "SemiSoilSensor.h"


// ==========================================
// OBJETOS PRINCIPALES
// ==========================================

semi::SequenceStore sequenceStore;

semi::SoilSensor soilSensor;



semi::ApiBridge backend;


// Bloqueo de movimiento físico
#ifndef SEMI_MOTOR_KEY
static_assert(
    !semi::MotorAdapter::physicalMotionImplemented,
    "Gate 6 no permite control fisico de motores."
);
#endif


// ==========================================
// VARIABLES DE ESTADO
// ==========================================

int lastAdcRaw = -1;

uint32_t lastAdcMs = 0;

bool diagnosticReady = false;

semi::LinkState lastPrintedState =
    semi::LinkState::NotConfigured;


// ==========================================
// CONFIGURACIÓN INICIAL
// ==========================================

void setup() {
#ifdef SEMI_MOTOR_KEY
  semi::bench::beginSafe();
#endif

  // Inicialización del puerto serie
  Serial.begin(115200);

  // Tiempo para estabilizar el arranque
  delay(1500);

  Serial.println();
  Serial.println("==================================");
  Serial.println("          SEMI - GATE 6");
  Serial.println("==================================");

  Serial.println(
      "[SEMI] Iniciando firmware de diagnostico..."
  );

  Serial.println(
      "[SEMI] Inicio con motores desactivados."
  );


  // ========================================
  // PERSISTENCIA DE SECUENCIAS
  // ========================================

  Serial.println(
      "[SEMI] Inicializando almacenamiento NVS..."
  );

  if (!sequenceStore.begin()) {

    Serial.println(
        "[SEMI] ERROR: no se pudo inicializar NVS."
    );

    Serial.println(
        "[SEMI] Comunicacion con Django deshabilitada."
    );

    return;
  }

  Serial.println(
      "[SEMI] Almacenamiento NVS inicializado."
  );


  // ========================================
  // SENSOR DE HUMEDAD
  // ========================================

  Serial.println(
      "[SEMI] Inicializando sensor capacitivo..."
  );

  soilSensor.begin();

  Serial.printf("[SEMI] Sensor configurado en GPIO%u.\n", semi::SoilSensor::kPin);


  // ========================================
  // CONFIGURACIÓN DEL BACKEND
  // ========================================

  Serial.println(
      "[SEMI] Preparando configuracion de red..."
  );

  semi::Config config;

  config.ssid = SEMI_WIFI_SSID;

  config.password = SEMI_WIFI_PASSWORD;

  config.backendUrl = SEMI_BACKEND_URL;

  config.deviceId = SEMI_DEVICE_ID;

  config.deviceToken = SEMI_DEVICE_TOKEN;

  config.sessionId = SEMI_SESSION_ID;

  config.samplingPointId = SEMI_SAMPLING_POINT_ID;


  // ========================================
  // INICIALIZACIÓN DEL API BRIDGE
  // ========================================

  Serial.println(
      "[SEMI] Inicializando puente ESP32-Django..."
  );

  if (!backend.begin(config, sequenceStore)) {

    Serial.println(
        "[SEMI] ERROR: configuracion del bridge invalida."
    );

    Serial.println(
        "[SEMI] Revisar semi_config.h:"
    );

    Serial.println(
        "[SEMI] - URL del backend"
    );

    Serial.println(
        "[SEMI] - ID del dispositivo"
    );

    Serial.println(
        "[SEMI] - Token de autenticacion"
    );

    Serial.println(
        "[SEMI] - UUID de sesion"
    );

    return;
  }


  // ========================================
  // DIAGNÓSTICO LISTO
  // ========================================

  diagnosticReady = true;
#ifdef SEMI_MOTOR_KEY
  semi::bench::start();
#endif

  Serial.println();
  Serial.println("==================================");

  Serial.println(
      "[SEMI] Inicializacion completada."
  );

  Serial.println(
      "[SEMI] Iniciando ciclo de diagnostico."
  );

  Serial.println(
      "[SEMI] Esperando conexion con Django..."
  );

  Serial.println("==================================");
  Serial.println();



}


// ==========================================
// CICLO PRINCIPAL
// ==========================================

void loop() {

  // ========================================
  // VERIFICACIÓN DEL ESTADO INICIAL
  // ========================================

  if (!diagnosticReady) {

    Serial.println(
        "[SEMI] ERROR: inicializacion incompleta."
    );

    Serial.println(
        "[SEMI] Revisar configuracion, NVS y mensajes de arranque."
    );

    delay(3000);

    return;
  }


  // ========================================
  // RELOJ DEL SISTEMA
  // ========================================

  const uint32_t now = millis();


  // ========================================
  // LECTURA DEL SENSOR
  // ========================================

  if (
      lastAdcRaw < 0 ||
      now - lastAdcMs >= 3000
  ) {

    lastAdcRaw = soilSensor.readRaw();

    lastAdcMs = now;

    Serial.print(
        "[SEMI] ADC sin calibrar ADC1: "
    );

    Serial.print(lastAdcRaw);

    Serial.println(" / 4095");
  }


  // ========================================
  // COMUNICACIÓN CON DJANGO
  // ========================================

  backend.service(lastAdcRaw);


  // ========================================
  // DETECCIÓN DE CAMBIOS DE CONEXIÓN
  // ========================================

  if (
      backend.state() != lastPrintedState
  ) {

    lastPrintedState = backend.state();

    Serial.print(
        "[SEMI] Estado de red: "
    );

    Serial.println(
        static_cast<unsigned int>(
            lastPrintedState
        )
    );
  }


  // ========================================
  // PEQUEÑA PAUSA DEL CICLO
  // ========================================

  delay(30);
}