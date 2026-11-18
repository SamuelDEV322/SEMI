#pragma once

// SEMI Gate 6: puente exclusivamente DIAGNOSTICO, contrato Gate 5 v1.0.
// No interpreta ordenes como permiso de locomocion ni controla GPIO/PWM.
// Arduino-ESP32 + ArduinoJson 7. Red HTTP solo en LAN de confianza.

#include <Arduino.h>
#include <ArduinoJson.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <cctype>
#include <cstring>
#include "SemiSequenceStore.h"

namespace semi {

enum class LinkState : uint8_t {
  NotConfigured, WifiDisconnected, BackendUnavailable,
  DiagnosticConnected, ProtocolBlocked
};

struct Config {
  const char* ssid;
  const char* password;
  const char* backendUrl;       // http://IP_DEL_PC:8000 (nunca localhost)
  const char* deviceId;         // ID previamente registrado en Django
  const char* deviceToken;      // Token secreto, min. 32 caracteres
  const char* sessionId;        // UUID generado por register_device
  uint32_t samplingPointId = 0; // 0 => omitir, nunca inventar posicion
};

class ApiBridge {
 public:
  bool begin(const Config& config, SequenceStore& store) {
    config_ = config;
    sequences_ = &store;
    if (!config_.ssid || !config_.password || !config_.backendUrl ||
        !config_.deviceId || !config_.deviceToken || !config_.sessionId ||
        strlen(config_.ssid) == 0 || strlen(config_.deviceId) == 0 ||
        strlen(config_.deviceToken) < 32 ||
        strlen(config_.deviceToken) > 512 ||
        !isUuid(config_.sessionId)) {
      state_ = LinkState::NotConfigured;
      return false;
    }
    baseUrl_ = config_.backendUrl;
    while (baseUrl_.endsWith("/")) baseUrl_.remove(baseUrl_.length() - 1);
    if (!baseUrl_.startsWith("http://") ||
        baseUrl_.startsWith("http://127.") ||
        baseUrl_.startsWith("http://localhost")) {
      state_ = LinkState::NotConfigured;
      return false;
    }
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(config_.ssid, config_.password);
    state_ = LinkState::WifiDisconnected;
    bootMs_ = millis();
    lastWifiAttemptMs_ = bootMs_;
    return true;
  }

  // Invocar en cada loop. HTTP sincrono: NUNCA usarlo como watchdog motor.
  void service(int soilAdcRaw) {
    if (state_ == LinkState::NotConfigured ||
        state_ == LinkState::ProtocolBlocked) return;

    const uint32_t now = millis();
    if (WiFi.status() != WL_CONNECTED) {
      state_ = LinkState::WifiDisconnected;
      if (now - lastWifiAttemptMs_ >= kWifiRetryMs) {
        lastWifiAttemptMs_ = now;
        WiFi.reconnect();
      }
      return;
    }

    // Health verifica el perfil del servidor; no es una autorizacion de motor.
    if (!healthy_ || now - lastHealthMs_ >= kHealthIntervalMs) {
      if (now - lastHealthAttemptMs_ >= kHealthRetryMs) {
        lastHealthAttemptMs_ = now;
        if (!checkHealth()) return;
        lastHealthMs_ = millis();
      }
    }
    if (!healthy_) return;

    // En cada canal, una peticion incierta se reintenta con el MISMO cuerpo.
    if (!statusPending_.length() &&
        (!sentStatus_ || now - lastStatusMs_ >= kStatusIntervalMs)) {
      if (!makeStatus()) return;
    }
    if (statusPending_.length() && now - lastStatusAttemptMs_ >= kRetryMs) {
      lastStatusAttemptMs_ = millis();
      sendPending("/api/device/status/", statusPending_, sentStatus_,
                  lastStatusMs_);
    }
    if (state_ == LinkState::ProtocolBlocked) return;

    if (!telemetryPending_.length() &&
        (!sentTelemetry_ || now - lastTelemetryMs_ >= kTelemetryIntervalMs)) {
      if (!makeTelemetry(soilAdcRaw)) return;
    }
    if (telemetryPending_.length() &&
        now - lastTelemetryAttemptMs_ >= kRetryMs) {
      lastTelemetryAttemptMs_ = millis();
      sendPending("/api/device/telemetry/", telemetryPending_,
                  sentTelemetry_, lastTelemetryMs_);
    }
    if (state_ == LinkState::ProtocolBlocked) return;

    if (now - lastPollMs_ >= kPollIntervalMs) {
      lastPollMs_ = millis();
      pollStopOnly();
    }
  }

  LinkState state() const { return state_; }
  bool motionAuthorized() const { return false; }
  bool hasPendingTelemetry() const { return telemetryPending_.length() != 0; }
  bool hasPendingStatus() const { return statusPending_.length() != 0; }

 private:
  enum class Result : uint8_t { Accepted, Transient, Rejected };
  static constexpr uint32_t kWifiRetryMs = 5000;
  static constexpr uint32_t kHealthRetryMs = 2500;
  static constexpr uint32_t kHealthIntervalMs = 15000;
  static constexpr uint32_t kStatusIntervalMs = 5000;
  static constexpr uint32_t kTelemetryIntervalMs = 15000;
  static constexpr uint32_t kPollIntervalMs = 5000;
  static constexpr uint32_t kRetryMs = 2000;
  static constexpr int kHttpTimeoutMs = 1800;

  Config config_{};
  SequenceStore* sequences_ = nullptr;
  String baseUrl_;
  LinkState state_ = LinkState::NotConfigured;
  bool healthy_ = false, sentStatus_ = false, sentTelemetry_ = false;
  String statusPending_, telemetryPending_;
  uint32_t bootMs_ = 0, lastWifiAttemptMs_ = 0;
  uint32_t lastHealthAttemptMs_ = 0, lastHealthMs_ = 0;
  uint32_t lastStatusMs_ = 0, lastTelemetryMs_ = 0, lastPollMs_ = 0;
  uint32_t lastStatusAttemptMs_ = 0, lastTelemetryAttemptMs_ = 0;

  static bool isUuid(const char* value) {
    if (!value || strlen(value) != 36) return false;
    for (int i = 0; i < 36; ++i) {
      if (i == 8 || i == 13 || i == 18 || i == 23) {
        if (value[i] != '-') return false;
      } else if (!isxdigit(static_cast<unsigned char>(value[i]))) {
        return false;
      }
    }
    return true;
  }

  bool validEnvelope(const JsonDocument& doc) const {
    return doc["schema_version"] == "1.0" &&
           doc["mode"] == "operational" &&
           doc["data"].is<JsonObjectConst>();
  }

  Result request(const String& method, const String& path,
                 const String* payload, JsonDocument& answer) {
    if (WiFi.status() != WL_CONNECTED) {
      healthy_ = false;
      state_ = LinkState::WifiDisconnected;
      return Result::Transient;
    }
    WiFiClient socket;
    HTTPClient http;
    http.setConnectTimeout(kHttpTimeoutMs);
    http.setTimeout(kHttpTimeoutMs);
    if (!http.begin(socket, baseUrl_ + path)) return Result::Transient;
    http.addHeader("Accept", "application/json");
    http.addHeader("X-SEMI-Device-ID", config_.deviceId);
    http.addHeader("X-SEMI-Device-Token", config_.deviceToken);

    int code = -1;
    if (method == "POST" && payload) {
      http.addHeader("Content-Type", "application/json");
      code = http.POST(*payload);
    } else if (method == "GET") {
      code = http.GET();
    }
    if (code < 200 || code >= 300) {
      http.end();
      if (code == 401 || code == 403 || code == 409 || code == 400 ||
          code == 404 || code == 413 || code == 415) {
        state_ = LinkState::ProtocolBlocked;
        Serial.printf("SEMI: protocolo/registro rechazado (HTTP %d).\n", code);
        return Result::Rejected;
      }
      state_ = LinkState::BackendUnavailable;
      return Result::Transient; // 503, 5xx, timeout, conexion fallida.
    }
    String response = http.getString();
    http.end();
    if (deserializeJson(answer, response) || !validEnvelope(answer)) {
      state_ = LinkState::ProtocolBlocked;
      Serial.println("SEMI: respuesta incompatible; revisar contrato.");
      return Result::Rejected;
    }
    state_ = LinkState::DiagnosticConnected;
    return Result::Accepted;
  }

  bool checkHealth() {
    JsonDocument response;
    Result outcome = request("GET", "/api/health/", nullptr, response);
    if (outcome != Result::Accepted) {
      healthy_ = false;
      return false;
    }
    JsonVariantConst info = response["data"];
    healthy_ = (info["physical_control"] == false || info["supervised_control"] == true) &&
               info["device_integration"] == "diagnostic";
    if (!healthy_) {
      state_ = LinkState::ProtocolBlocked;
      Serial.println("SEMI: backend no esta en operational + diagnostic.");
    }
    return healthy_;
  }

  bool makeTelemetry(int raw) {
    if (raw < 0 || raw > 4095) {
      Serial.println("SEMI: ADC fuera de rango; no se envia.");
      return false;
    }
    uint32_t seq;
    if (!sequences_->nextTelemetry(seq)) return blockOnSequenceFailure();
    JsonDocument data;
    data["schema_version"] = "1.0";
    data["session_id"] = config_.sessionId;
    data["message_id"] = uuidV4();
    data["seq"] = seq;
    data["measured_at"] = nullptr;  // Sin RTC validado.
    if (config_.samplingPointId > 0)
      data["sampling_point_id"] = config_.samplingPointId;
    JsonObject sensor = data["sensors"]["soil_moisture_adc"].to<JsonObject>();
    sensor["value"] = raw;
    sensor["adc_max"] = 4095;
    sensor["status"] = raw == 0 ? "invalid" : "valid";  // Valor de ADC plausible, NO calibrado.
    if (!serializeJson(data, telemetryPending_)) return blockOnSequenceFailure();
    return telemetryPending_.length() > 0;
  }

  bool makeStatus() {
    uint32_t seq;
    if (!sequences_->nextStatus(seq)) return blockOnSequenceFailure();
    JsonDocument data;
    data["schema_version"] = "1.0";
    data["session_id"] = config_.sessionId;
    data["message_id"] = uuidV4();
    data["seq"] = seq;
    data["measured_at"] = nullptr;
#ifdef SEMI_MOTOR_KEY
    data["firmware"] = "SEMI-Gate6.4-Supervised/1.0";
#else
    data["firmware"] = "SEMI-Gate6-Diagnostic/0.1";
#endif
    data["uptime_ms"] = static_cast<uint32_t>(millis() - bootMs_);
    data["firmware_state"] = "ready";
    data["reported_motion"] = "unknown"; // No se verifica estado fisico.
    data["capabilities"]["telemetry"] = true;
#if defined(SEMI_MOTOR_KEY) && SEMI_TRACTION_VERIFIED
    data["capabilities"]["motion"] = true; // Build capability, never an arm grant.
#else
    data["capabilities"]["motion"] = false;
#endif
    data["errors"].to<JsonArray>();
    if (!serializeJson(data, statusPending_)) return blockOnSequenceFailure();
    return statusPending_.length() > 0;
  }

  bool blockOnSequenceFailure() {
    state_ = LinkState::ProtocolBlocked;
    Serial.println("SEMI: error/agotamiento de secuencias NVS.");
    return false;
  }

  void sendPending(const String& path, String& payload, bool& sent,
                   uint32_t& lastSentMs) {
    JsonDocument response;
    Result outcome = request("POST", path, &payload, response);
    if (outcome == Result::Accepted) {
      // Valida correlacion antes de descartar la copia idempotente.
      JsonDocument original;
      if (deserializeJson(original, payload) ||
          String(response["data"]["message_id"] | "") !=
              String(original["message_id"] | "") ||
          response["data"]["seq"].as<uint32_t>() !=
              original["seq"].as<uint32_t>()) {
        state_ = LinkState::ProtocolBlocked;
        Serial.println("SEMI: recibo del servidor no corresponde al envio.");
        return;
      }
      payload = "";
      sent = true;
      lastSentMs = millis();
      Serial.printf("SEMI: %s aceptado.\n", path.c_str());
    }
  }

  void pollStopOnly() {
    uint32_t seq;
    if (!sequences_->nextPoll(seq)) {
      blockOnSequenceFailure();
      return;
    }
    const String path = String("/api/device/commands/next/?schema_version=1.0") +
                        "&session_id=" + config_.sessionId +
                        "&request_id=" + uuidV4() +
                        "&seq=" + String(seq);
    JsonDocument response;
    Result outcome = request("GET", path, nullptr, response);
    if (outcome != Result::Accepted) return;
    JsonVariantConst data = response["data"];
    if (data["action"] != "stop" || data["motion_enabled"] != false ||
        data["authorization"] != "diagnostic_only" ||
        data["session_id"] != config_.sessionId) {
      state_ = LinkState::ProtocolBlocked;
      Serial.println("SEMI: orden no STOP; ignorada por seguridad.");
    }
    // No existe ejecucion de ordenes, NI siquiera para STOP por red.
    // Los motores no se configuran y las entradas del adaptador son inertes.
  }
};

}  // namespace semi
