// src/wifi_manager.cpp
#include <Arduino.h>
#include <WiFiS3.h>
#include "wifi_manager.h"

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #include "secrets_exam.h"
#endif

static void logw(const __FlashStringHelper* msg) {
  Serial.print(F("[WARN] "));
  Serial.println(msg);
}

bool wifi_is_connected() {
  return WiFi.status() == WL_CONNECTED;
}

void wifi_connect_blocking() {
  Serial.print(F("[WIFI] connecting to "));
  Serial.println(WIFI_SSID);

  int status = WL_IDLE_STATUS;
  uint32_t t0 = millis();

  while (status != WL_CONNECTED) {
    status = WiFi.begin(WIFI_SSID, WIFI_PASS);
    delay(1000);

    Serial.print(F("[WIFI] status="));
    Serial.println(status);

    if (millis() - t0 > 20000) {
      logw(F("WIFI: still trying..."));
      t0 = millis();
    }
  }

  Serial.print(F("[WIFI] connected. ip="));
  Serial.println(WiFi.localIP());
}

void wifi_ensure_connected() {
  if (wifi_is_connected()) return;

  logw(F("WIFI: disconnected -> reconnect"));
  WiFi.disconnect();
  delay(200);
  wifi_connect_blocking();
}
