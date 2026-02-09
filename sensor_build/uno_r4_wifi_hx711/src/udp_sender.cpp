#include <Arduino.h>
#include <WiFiUdp.h>
#include "udp_sender.h"

#if __has_include("secrets.h")
  #include "secrets.h"
#else
  #include "secrets_exam.h"
#endif

static WiFiUDP udp;
static uint32_t seq = 0;
static IPAddress recv_ip(RECV_IP_A, RECV_IP_B, RECV_IP_C, RECV_IP_D);

void udp_sender_begin() {
  udp.begin(0); // 송신만이면 임의 로컬 포트 OK
}

void udp_sender_send_weight(float weight_kg) {
  char payload[128];
  uint32_t ts = millis();

  snprintf(payload, sizeof(payload),
           "{\"weight_kg\":%.3f,\"ts\":%lu,\"seq\":%lu}",
           (double)weight_kg, (unsigned long)ts, (unsigned long)seq);

  udp.beginPacket(recv_ip, (uint16_t)RECV_PORT);
  udp.write((const uint8_t*)payload, strlen(payload));
  udp.endPacket();

  seq++;
}
