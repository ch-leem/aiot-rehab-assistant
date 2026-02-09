#include "udp_sender.h"
#include <Arduino.h>
#include <WiFiUdp.h>

static WiFiUDP g_udp;
static UdpConfig g_cfg;

bool udpBegin(const UdpConfig& cfg) {
  g_cfg = cfg;

  // 송신만 해도 되지만, 포트 바인딩을 해두면 디버그 때 편함
  // (원하면 0 대신 특정 로컬 포트로 바꿔도 됨)
  return g_udp.begin(0);
}

bool udpSendLine(const char* line) {
  if (WiFi.status() != WL_CONNECTED) return false;

  if (!g_udp.beginPacket(g_cfg.targetIP, g_cfg.targetPort)) return false;
  g_udp.write((const uint8_t*)line, strlen(line));
  return (g_udp.endPacket() == 1);
}
