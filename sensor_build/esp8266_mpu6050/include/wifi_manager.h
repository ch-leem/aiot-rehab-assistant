#pragma once
#include <ESP8266WiFi.h>

struct WifiConfig {
  const char* ssid;
  const char* pass;

  bool useStaticIP;
  IPAddress localIP;
  IPAddress gateway;
  IPAddress subnet;
  IPAddress dns1;
  IPAddress dns2;

  uint32_t connectTimeoutMs;
};

bool wifiConnect(const WifiConfig& cfg);
void wifiEnsureConnected(const WifiConfig& cfg);
