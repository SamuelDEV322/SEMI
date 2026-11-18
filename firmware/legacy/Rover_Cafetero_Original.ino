// ==========================================
// Rover cafetero ESP32
// TB6612FNG + L298N + sensor capacitivo
// ==========================================

// ---------- TB6612FNG: motores de tracción ----------
#define PWMA 2
#define AIN1 5
#define AIN2 4
#define STBY 15

#define PWMB 25
#define BIN1 26
#define BIN2 27

// ---------- L298N: motor de cremallera ----------
#define IN3 19
#define IN4 21
#define ENB 18

// ---------- Sensor capacitivo ----------
#define SOIL_PIN 34

// ---------- PWM ----------
#define FRECUENCIA_PWM 1000 // Hz
#define RESOLUCION_PWM 8    // 0 a 255

#define CANAL_MOTOR_A 0
#define CANAL_MOTOR_B 1
#define CANAL_CREMALLERA 2

// Velocidad inicial de prueba
int velocidadRover = 150;       // 0 a 255
int velocidadCremallera = 120;  // 0 a 255

// Calibración del sensor
const int SOIL_DRY = 3200; // Cambiar según tu prueba en suelo seco
const int SOIL_WET = 1500; // Cambiar según tu prueba en suelo húmedo

// ==========================================
// Funciones del TB6612FNG
// ==========================================

void configurarTB6612() {
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);
  pinMode(STBY, OUTPUT);

  ledcSetup(CANAL_MOTOR_A, FRECUENCIA_PWM, RESOLUCION_PWM);
  ledcAttachPin(PWMA, CANAL_MOTOR_A);

  ledcSetup(CANAL_MOTOR_B, FRECUENCIA_PWM, RESOLUCION_PWM);
  ledcAttachPin(PWMB, CANAL_MOTOR_B);

  digitalWrite(STBY, HIGH); // Habilita el driver

  detenerRover();
}

void moverMotorA(int velocidad) {
  velocidad = constrain(velocidad, -255, 255);

  if (velocidad > 0) {
    digitalWrite(AIN1, HIGH);
    digitalWrite(AIN2, LOW);
  }
  else if (velocidad < 0) {
    digitalWrite(AIN1, LOW);
    digitalWrite(AIN2, HIGH);
    velocidad = -velocidad;
  }
  else {
    digitalWrite(AIN1, LOW);
    digitalWrite(AIN2, LOW);
  }

  ledcWrite(CANAL_MOTOR_A, velocidad);
}

void moverMotorB(int velocidad) {
  velocidad = constrain(velocidad, -255, 255);

  if (velocidad > 0) {
    digitalWrite(BIN1, HIGH);
    digitalWrite(BIN2, LOW);
  }
  else if (velocidad < 0) {
    digitalWrite(BIN1, LOW);
    digitalWrite(BIN2, HIGH);
    velocidad = -velocidad;
  }
  else {
    digitalWrite(BIN1, LOW);
    digitalWrite(BIN2, LOW);
  }

  ledcWrite(CANAL_MOTOR_B, velocidad);
}

void avanzar(int velocidad) {
  moverMotorA(velocidad);
  moverMotorB(velocidad);
}

void retroceder(int velocidad) {
  moverMotorA(-velocidad);
  moverMotorB(-velocidad);
}

void girarDerecha(int velocidad) {
  moverMotorA(velocidad);
  moverMotorB(-velocidad);
}

void girarIzquierda(int velocidad) {
  moverMotorA(-velocidad);
  moverMotorB(velocidad);
}

void detenerRover() {
  moverMotorA(0);
  moverMotorB(0);
}

// ==========================================
// Funciones del L298N: cremallera
// ==========================================

void configurarCremallera() {
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  ledcSetup(CANAL_CREMALLERA, FRECUENCIA_PWM, RESOLUCION_PWM);
  ledcAttachPin(ENB, CANAL_CREMALLERA);

  detenerCremallera();
}

void moverCremallera(int velocidad) {
  velocidad = constrain(velocidad, -255, 255);

  if (velocidad > 0) {
    digitalWrite(IN3, HIGH);
    digitalWrite(IN4, LOW);
  }
  else if (velocidad < 0) {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, HIGH);
    velocidad = -velocidad;
  }
  else {
    digitalWrite(IN3, LOW);
    digitalWrite(IN4, LOW);
  }

  ledcWrite(CANAL_CREMALLERA, velocidad);
}

void subirCremallera(int velocidad) {
  moverCremallera(velocidad);
}

void bajarCremallera(int velocidad) {
  moverCremallera(-velocidad);
}

void detenerCremallera() {
  moverCremallera(0);
}

// ==========================================
// Sensor capacitivo de humedad
// ==========================================

float leerHumedad() {
  int lectura = analogRead(SOIL_PIN);

  int humedad = map(lectura, SOIL_DRY, SOIL_WET, 0, 100);
  humedad = constrain(humedad, 0, 100);

  Serial.print("ADC: ");
  Serial.print(lectura);
  Serial.print(" | Humedad estimada: ");
  Serial.print(humedad);
  Serial.println(" %");

  return humedad;
}

// ==========================================
// Configuración inicial
// ==========================================

void setup() {
  Serial.begin(115200);

  configurarTB6612();
  configurarCremallera();

  analogReadResolution(12); // Lecturas de 0 a 4095

  Serial.println("Rover cafetero listo");
}

// ==========================================
// Prueba de movimiento
// ==========================================

void loop() {
  leerHumedad();

  // Prueba segura del rover
  Serial.println("Avanzando");
  avanzar(velocidadRover);
  delay(1500);

  Serial.println("Deteniendo");
  detenerRover();
  delay(1000);

  // Prueba segura de la cremallera
  Serial.println("Subiendo cremallera");
  subirCremallera(velocidadCremallera);
  delay(1500);

  Serial.println("Deteniendo cremallera");
  detenerCremallera();
  delay(1000);

  Serial.println("Bajando cremallera");
  bajarCremallera(velocidadCremallera);
  delay(1500);

  Serial.println("Deteniendo cremallera");
  detenerCremallera();
  delay(2000);
}
