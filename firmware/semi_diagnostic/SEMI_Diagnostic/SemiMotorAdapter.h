#pragma once

#include <Arduino.h>

namespace semi {

// Correspondencia con el sketch original del equipo mecatronico.
// GPIOs y controladores conservados SOLO como referencia documental.
// TB6612FNG: PWMA=2, AIN1=5, AIN2=4, STBY=15,
//             PWMB=25, BIN1=26, BIN2=27.
// L298N: IN3=19, IN4=21, ENB=18.
//
// GATE 6 DIAGNOSTIC ONLY:
// Este adaptador NO configura GPIO, PWM, STBY ni motores.
// No existe variable de entorno ni accion de red que desbloquee movimiento.
class MotorAdapter {
 public:
  bool avanzar(uint8_t) { return false; }
  bool retroceder(uint8_t) { return false; }
  bool girarDerecha(uint8_t) { return false; }
  bool girarIzquierda(uint8_t) { return false; }
  bool subirCremallera(uint8_t) { return false; }
  bool bajarCremallera(uint8_t) { return false; }
  void detenerRover() {}      // NO es una parada de emergencia fisica.
  void detenerCremallera() {} // NO es una parada de emergencia fisica.
  static constexpr bool physicalMotionImplemented = false;
};

}  // namespace semi
