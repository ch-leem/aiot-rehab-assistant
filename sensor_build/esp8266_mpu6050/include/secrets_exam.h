#pragma once
#include <ESP8266WiFi.h>

// 이 파일을 복사해서 include/secrets.h 로 만들고 값만 채워서 사용
// include/secrets.h 는 .gitignore로 커밋 금지

static const char* WIFI_SSID = "YOUR_SSID";
static const char* WIFI_PASS = "YOUR_PASSWORD";

// 고정 IP 사용 여부
static const bool WIFI_USE_STATIC = true;

// 고정 IP 설정 (네트워크에 맞게)
static const IPAddress WIFI_LOCAL_IP(, , , );
static const IPAddress WIFI_GATEWAY (, , , );
static const IPAddress WIFI_SUBNET  (, , , );

// DNS (회사망이면 명시 추천, 회사 DNS가 있으면 그걸 우선)
static const IPAddress WIFI_DNS1(, , , );
static const IPAddress WIFI_DNS2(, , , );

// == Jetson
static const IPAddress UDP_TARGET_IP(, , , ); // 네 PC IP로 바꿔
static const uint16_t  UDP_TARGET_PORT = 9999;
