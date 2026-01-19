#pragma once
#include <ESP8266WiFi.h>

struct UdpConfig {
  IPAddress targetIP;
  uint16_t targetPort;
};

bool udpBegin(const UdpConfig& cfg);
bool udpSendLine(const char* line);
