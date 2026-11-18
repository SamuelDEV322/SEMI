#pragma once

#include <Arduino.h>

namespace semi {

class SoilSensor {
 public:
  static constexpr uint8_t kPin = 34;  // GPIO34 / ADC1, ESP32 clasico.
  static constexpr int kAdcMax = 4095;

  void begin() {
    analogReadResolution(12);
    pinMode(kPin, INPUT);
  }

  // Media ADC sin calibracion agronomica. No detecta arena ni tipo de tierra.
  int readRaw() {
    uint32_t total = 0;
    constexpr uint8_t count = 8;
    for (uint8_t i = 0; i < count; ++i) {
      total += static_cast<uint32_t>(analogRead(kPin));
      delayMicroseconds(400);
    }
    return static_cast<int>((total + count / 2) / count);
  }
};

}  // namespace semi
