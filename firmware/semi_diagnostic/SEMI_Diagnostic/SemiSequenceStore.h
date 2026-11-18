#pragma once

#include <Arduino.h>
#include <Preferences.h>
#include <esp_system.h>

namespace semi {

// Persistencia por bloques: un reinicio salta los numeros no usados.
// Evita escribir flash en cada heartbeat y evita reusar secuencias previas.
// NUNCA resetea automaticamente la sesion del servidor.
class SequenceStore {
 public:
  bool begin() { return prefs_.begin("semi-gate6", false); }

  bool nextTelemetry(uint32_t& value) {
    return next("tele-next", telemetry_, value);
  }
  bool nextStatus(uint32_t& value) {
    return next("stat-next", status_, value);
  }
  bool nextPoll(uint32_t& value) {
    return next("poll-next", poll_, value);
  }

 private:
  struct Block {
    uint32_t next = 0;
    uint32_t end = 0;
  };

  Preferences prefs_;
  Block telemetry_{}, status_{}, poll_{};
  static constexpr uint32_t kBlock = 128;
  static constexpr uint32_t kMaxSequence = 2147483647UL;

  bool next(const char* key, Block& block, uint32_t& value) {
    if (block.next == block.end) {
      const uint32_t begin = prefs_.getULong(key, 0);
      if (begin > kMaxSequence - kBlock) return false;
      if (prefs_.putULong(key, begin + kBlock) != sizeof(uint32_t))
        return false;
      block.next = begin;
      block.end = begin + kBlock;
    }
    value = block.next++;
    return true;
  }
};

inline String uuidV4() {
  uint8_t bytes[16];
  esp_fill_random(bytes, sizeof(bytes));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  char id[37];
  snprintf(
      id, sizeof(id),
      "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-"
      "%02x%02x%02x%02x%02x%02x",
      bytes[0], bytes[1], bytes[2], bytes[3],
      bytes[4], bytes[5], bytes[6], bytes[7],
      bytes[8], bytes[9], bytes[10], bytes[11],
      bytes[12], bytes[13], bytes[14], bytes[15]);
  return String(id);
}

}  // namespace semi
