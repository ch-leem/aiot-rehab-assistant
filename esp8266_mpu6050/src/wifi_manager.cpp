#include "wifi_manager.h"
#include <Arduino.h>

static const char* wlStatusToStr(wl_status_t s) {
  switch (s) {
    case WL_IDLE_STATUS: return "IDLE";
    case WL_NO_SSID_AVAIL: return "NO_SSID_AVAIL";
    case WL_SCAN_COMPLETED: return "SCAN_COMPLETED";
    case WL_CONNECTED: return "CONNECTED";
    case WL_CONNECT_FAILED: return "CONNECT_FAILED";
    case WL_CONNECTION_LOST: return "CONNECTION_LOST";
    case WL_DISCONNECTED: return "DISCONNECTED";
    default: return "UNKNOWN";
  }
}

bool wifiConnect(const WifiConfig& cfg) {
  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);

  if (cfg.useStaticIP) {
    WiFi.config(cfg.localIP, cfg.gateway, cfg.subnet, cfg.dns1, cfg.dns2);
  }

  Serial.print("WiFi begin: ");
  Serial.println(cfg.ssid);

  WiFi.begin(cfg.ssid, cfg.pass);

  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
    Serial.print(".");

    if (millis() - t0 > cfg.connectTimeoutMs) {
      Serial.println();
      wl_status_t st = WiFi.status();
      Serial.print("WiFi timeout, status=");
      Serial.print((int)st);
      Serial.print(" (");
      Serial.print(wlStatusToStr(st));
      Serial.println(")");

      Serial.print("Seen SSID: ");
      Serial.println(WiFi.SSID());

      return false;
    }
  }

  Serial.println();
  Serial.print("WiFi connected, IP=");
  Serial.println(WiFi.localIP());
  return true;
}

void wifiEnsureConnected(const WifiConfig& cfg) {
  if (WiFi.status() == WL_CONNECTED) return;
  WiFi.disconnect();
  delay(100);
  wifiConnect(cfg);
}


