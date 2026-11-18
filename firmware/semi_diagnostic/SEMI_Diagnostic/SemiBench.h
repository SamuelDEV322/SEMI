#pragma once
// Included only in the explicitly configured supervised bench build (Arduino-ESP32 3.x).
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <mbedtls/md.h>
#include <esp_system.h>
#include <driver/gpio.h>
#include <esp_task_wdt.h>
#include "SemiBenchGuard.h"

#ifndef SEMI_TRACTION_VERIFIED
#define SEMI_TRACTION_VERIFIED 0
#endif
#ifndef SEMI_RACK_SUPERVISED
#define SEMI_RACK_SUPERVISED 0
#endif

namespace semi {
namespace bench {
constexpr int stby=15, pwma=2, ain1=5, ain2=4, pwmb=25, bin1=26, bin2=27;
constexpr int enb=18, in3=19, in4=21;
struct Frame { DriveDemand traction, rack; };
static QueueHandle_t inbox;
static unsigned readyBits;

inline void low(int pin) {
  gpio_set_level(static_cast<gpio_num_t>(pin), 0);
  pinMode(pin, OUTPUT);
  digitalWrite(pin, LOW);
}
inline void beginSafe() {
  // External hardware inhibits are essential while ESP32 pins are high impedance at reset.
  if (SEMI_TRACTION_VERIFIED) {
    for (int pin : {stby,pwma,pwmb,ain1,ain2,bin1,bin2}) low(pin);
    if (ledcAttach(pwma,1000,8) && ledcAttach(pwmb,1000,8) &&
        ledcWrite(pwma,0) && ledcWrite(pwmb,0)) readyBits |= 1;
  }
  if (SEMI_RACK_SUPERVISED) {
    for (int pin : {enb,in3,in4}) low(pin);
    if (ledcAttach(enb,1000,8) && ledcWrite(enb,0)) readyBits |= 2;
  }
}
inline void traction(int action, bool medium) {
  digitalWrite(stby, LOW);
  digitalWrite(ain1, action==1 || action==4);
  digitalWrite(ain2, action==2 || action==3);
  digitalWrite(bin1, action==1 || action==3);
  digitalWrite(bin2, action==2 || action==4);
  const unsigned duty = action ? (medium ? 120 : 80) : 0;
  if (ledcWrite(pwma,duty) && ledcWrite(pwmb,duty) && action) digitalWrite(stby,HIGH);
}
inline void rack(int action) {
  ledcWrite(enb,0);
  digitalWrite(in3,action==1);
  digitalWrite(in4,action==2);
  if (action) ledcWrite(enb,80);
}
inline void transport(void*);
inline void supervisor(void*) {
  // IDF task watchdog backs up the short command lease if this task stalls.
  esp_task_wdt_config_t wdt{};
  wdt.timeout_ms = 2000;
  wdt.idle_core_mask = 0;
  wdt.trigger_panic = true;
  esp_err_t configured = esp_task_wdt_init(&wdt);
  if (configured == ESP_ERR_INVALID_STATE) configured = esp_task_wdt_reconfigure(&wdt);
  if (configured != ESP_OK || esp_task_wdt_add(nullptr) != ESP_OK) {
    Serial.println("[SEMI] Watchdog no disponible. Mando bloqueado.");
    vTaskDelete(nullptr);
    return;
  }
  if (xTaskCreate(transport,"motor-poll",8192,nullptr,1,nullptr)!=pdPASS) {
    esp_task_wdt_delete(nullptr);
    vTaskDelete(nullptr);
    return;
  }
  BenchGuard wheels(1500), slide(300);
  Frame frame{};
  int lastT=-1, lastR=-1; bool lastMedium=false;
  for (;;) {
    xQueueReceive(inbox,&frame,0);
    const bool online = WiFi.status()==WL_CONNECTED;
    const uint32_t now=millis();
    int t=wheels.tick(now,online,frame.traction), r=slide.tick(now,online,frame.rack);
    if ((readyBits & 1) && (t!=lastT || lastMedium!=frame.traction.medium))
      traction(t,frame.traction.medium);
    if ((readyBits & 2) && r!=lastR) rack(r);
    lastT=t; lastR=r; lastMedium=frame.traction.medium;
    esp_task_wdt_reset();
    vTaskDelay(pdMS_TO_TICKS(5) ? pdMS_TO_TICKS(5) : 1);
  }
}
inline String signature(const String& message) {
  const char* key=SEMI_MOTOR_KEY;
  unsigned char digest[32]; char hex[65];
  if (mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),
      (const unsigned char*)key,strlen(key),(const unsigned char*)message.c_str(),
      message.length(),digest)) return "";
  for (int i=0;i<32;++i) snprintf(hex+2*i,3,"%02x",digest[i]);
  return String(hex);
}
inline bool decode(const char* action,const char* speed,int ttl,bool isRack,
                   uint32_t started, DriveDemand& d) {
  const char* names[]={"stop","forward","backward","left","right"};
  const char* slide[]={"stop","up","down"};
  if (strcmp(speed,"low") && strcmp(speed,"medium")) return false;
  for (int i=0;i<(isRack?3:5);++i) {
    if (strcmp(action,isRack?slide[i]:names[i])) continue;
    if ((!i && ttl!=0) || (i && (ttl<=0 || ttl>250))) return false;
    d={i,!strcmp(speed,"medium"), started+uint32_t(ttl)};
    return true;
  }
  return false;
}
inline bool poll(const String& boot, uint32_t count, Frame& frame) {
  WiFiClient socket; HTTPClient http;
  http.setConnectTimeout(180); http.setTimeout(220);
  String base=SEMI_BACKEND_URL;
  if (base.endsWith("/")) base.remove(base.length()-1);
  if (!http.begin(socket,base+"/api/device/bench/")) return false;
  http.addHeader("Content-Type","application/json");
  http.addHeader("X-SEMI-Device-ID",SEMI_DEVICE_ID);
  http.addHeader("X-SEMI-Device-Token",SEMI_DEVICE_TOKEN);
  JsonDocument d;
  d["schema_version"]="1.0"; d["session_id"]=SEMI_SESSION_ID; d["boot"]=boot;
  d["counter"]=count; d["ready"]=readyBits;
  d["mac"]=signature(String("poll|")+SEMI_DEVICE_ID+"|"+SEMI_SESSION_ID+"|"+boot+"|"+count+"|"+readyBits);
  String body; serializeJson(d,body);
  uint32_t started=millis();
  if (http.POST(body)!=200) return false;
  String raw=http.getString();
  if (millis()-started>=250 || raw.length()>1024 || deserializeJson(d,raw)) return false;
  String msg=d["data"]["frame"] | "";
  String sig=signature(msg);
  String prefix=String("reply|")+boot+"|"+count+"|";
  if (!sig.length() || sig!=String(d["data"]["mac"] | "") || !msg.startsWith(prefix)) return false;
  char t[10],ts[8],r[10],rs[8],extra;
  int tt=0,rt=0;
  if (sscanf(msg.c_str()+prefix.length(),"%9[^|]|%7[^|]|%d|%9[^|]|%7[^|]|%d%c",
             t,ts,&tt,r,rs,&rt,&extra)!=6) return false;
  return decode(t,ts,tt,false,started,frame.traction) && decode(r,rs,rt,true,started,frame.rack);
}
inline void transport(void*) {
  char boot[33]={}; uint32_t count=0;
  for (;;) {
    Frame frame{};
    if (!count) {
      for (unsigned i=0;i<4;++i) snprintf(boot+8*i,9,"%08lx",(unsigned long)esp_random());
    }
    bool ok=WiFi.status()==WL_CONNECTED && count<0x7fffffff && poll(boot,++count,frame);
    if (!ok) { frame={}; count=0; }
    xQueueOverwrite(inbox,&frame);
    vTaskDelay(pdMS_TO_TICKS(ok?50:350));
  }
}
inline void start() {
  if (!readyBits || strlen(SEMI_MOTOR_KEY)<32) return;
  inbox=xQueueCreate(1,sizeof(Frame));
  if (inbox) xTaskCreate(supervisor,"motor-watch",4096,nullptr,4,nullptr);
}
}
}

