// src/main.cpp
#include <Arduino.h>
#include <EEPROM.h>
#include <math.h>
#include "HX711.h"

#include "wifi_manager.h"
#include "udp_sender.h"

// ===================== 사용자 설정 =====================
static const int HX711_DOUT_PIN = 3;
static const int HX711_SCK_PIN  = 2;

// 10Hz
static const uint32_t PERIOD_MS = 100;

// 필터
static const int   MED_N = 5;           // median window (odd)
static const float EMA_ALPHA = 0.30f;   // 0.25~0.35 추천

// Zero tracking
static const float   ZERO_BAND_KG = 0.05f;      // ±50g 이하면 빈 상태 후보
static const uint16_t ZERO_HOLD_SAMPLES = 25;   // 10Hz 기준 2.5초
static const float   OFFSET_ADAPT = 0.02f;      // offset 적응 속도

// EEPROM
static const int EEPROM_ADDR_CAL   = 0;   // float
static const int EEPROM_ADDR_MAGIC = 8;   // uint32_t
static const uint32_t MAGIC = 0xC0A1BEEF;

// ===================== 전역 =====================
static HX711 scale;

static long  offset_raw = 0;
static float cal_factor = 1000.0f; // counts per gram fallback

static uint32_t last_ms = 0;

// median buffer
static long med_buf[MED_N];
static int  med_i = 0;
static bool med_full = false;

// EMA state
static float ema_kg = 0.0f;
static bool  ema_init = false;

// zero tracking state
static uint16_t zero_cnt = 0;

// ===================== 로그 헬퍼 =====================
static void logi(const __FlashStringHelper* msg) {
  Serial.print(F("[INFO] "));
  Serial.println(msg);
}
static void logw(const __FlashStringHelper* msg) {
  Serial.print(F("[WARN] "));
  Serial.println(msg);
}
static void logv_kv(const __FlashStringHelper* k, float v, int prec = 6) {
  Serial.print(F("[INFO] "));
  Serial.print(k);
  Serial.print(F("="));
  Serial.println(v, prec);
}

// ===================== EEPROM =====================
static bool loadCalFactor() {
  uint32_t m = 0;
  EEPROM.get(EEPROM_ADDR_MAGIC, m);
  if (m != MAGIC) return false;

  float v = 0.0f;
  EEPROM.get(EEPROM_ADDR_CAL, v);
  if (isnan(v) || v < 0.001f || v > 1e6f) return false;

  cal_factor = v;
  return true;
}

static void saveCalFactor(float v) {
  EEPROM.put(EEPROM_ADDR_CAL, v);
  EEPROM.put(EEPROM_ADDR_MAGIC, MAGIC);
}

// ===================== HX711 / 필터 =====================
static long readRawBlocking() {
  return scale.read(); // HX711 10Hz면 여기서 대기(정상)
}

static long medianOfN(const long a[MED_N]) {
  long t[MED_N];
  for (int i = 0; i < MED_N; i++) t[i] = a[i];

  for (int i = 0; i < MED_N - 1; i++) {
    for (int j = i + 1; j < MED_N; j++) {
      if (t[j] < t[i]) { long tmp = t[i]; t[i] = t[j]; t[j] = tmp; }
    }
  }
  return t[MED_N / 2];
}

static void filterReset() {
  med_i = 0;
  med_full = false;
  ema_init = false;
  zero_cnt = 0;
}

static float rawToKg(long raw) {
  long delta = raw - offset_raw;
  float g = (float)delta / cal_factor;

  // 0 근처 미세 흔들림 컷
  if (g > -2.0f && g < 2.0f) g = 0.0f;

  return g / 1000.0f;
}

static float filteredKgFromRaw(long raw) {
  med_buf[med_i] = raw;
  med_i++;
  if (med_i >= MED_N) { med_i = 0; med_full = true; }

  long use_raw = raw;
  if (med_full) use_raw = medianOfN(med_buf);

  float kg = rawToKg(use_raw);
  if (!ema_init) {
    ema_kg = kg;
    ema_init = true;
  } else {
    ema_kg = EMA_ALPHA * kg + (1.0f - EMA_ALPHA) * ema_kg;
  }

  return ema_kg;
}

// ===================== Zero tracking =====================
static void zeroTrackingUpdate(long raw_now, float kg_filtered) {
  if (fabsf(kg_filtered) <= ZERO_BAND_KG) {
    if (zero_cnt < 60000) zero_cnt++;
  } else {
    zero_cnt = 0;
  }

  if (zero_cnt >= ZERO_HOLD_SAMPLES) {
    float new_off = (1.0f - OFFSET_ADAPT) * (float)offset_raw + OFFSET_ADAPT * (float)raw_now;
    long prev = offset_raw;
    offset_raw = (long)lroundf(new_off);

    zero_cnt = ZERO_HOLD_SAMPLES - 5;

    if (offset_raw != prev) {
      Serial.print(F("[ZERO] offset_raw="));
      Serial.println(offset_raw);
    }
  }
}

// ===================== Tare / Calibrate =====================
static void tareScale() {
  logi(F("TARE: remove weight and keep still"));
  delay(300);

  long s = 0;
  for (int i = 0; i < 20; i++) s += readRawBlocking();
  offset_raw = s / 20;

  filterReset();
  Serial.print(F("[TARE] offset_raw="));
  Serial.println(offset_raw);
}

static void calibrateScaleInteractive() {
  logi(F("CAL: put KNOWN weight, type grams then Enter (e.g., 5000)"));

  while (!Serial.available()) delay(10);
  float known_g = Serial.parseFloat();
  while (Serial.available()) Serial.read();

  if (known_g <= 0) {
    logw(F("CAL: invalid grams"));
    return;
  }

  delay(500);

  long s = 0;
  for (int i = 0; i < 25; i++) s += readRawBlocking();
  long raw_loaded = s / 25;
  long delta = raw_loaded - offset_raw;

  if (delta == 0) {
    logw(F("CAL: delta=0 (check wiring/placement)"));
    return;
  }

  cal_factor = (float)delta / known_g;
  saveCalFactor(cal_factor);

  filterReset();

  Serial.print(F("[CAL] cal_factor(counts/g)="));
  Serial.println(cal_factor, 6);
}

// ===================== setup/loop =====================
void setup() {
  Serial.begin(115200);
  delay(200);

  logi(F("PIO UNO R4 WiFi | HX711 -> UDP (10Hz)"));
  Serial.println(F("[CMD] t=tare, c=calibrate"));

  scale.begin(HX711_DOUT_PIN, HX711_SCK_PIN);

  if (loadCalFactor()) logv_kv(F("cal_factor(counts/g)"), cal_factor, 6);
  else logw(F("no saved cal_factor. Run 'c' once."));

  wifi_connect_blocking();
  udp_sender_begin();

  delay(1200);
  (void)readRawBlocking();

  tareScale();

  logi(F("Ready. Sending UDP"));
}

void loop() {
  if (Serial.available()) {
    char ch = Serial.read();
    if (ch == 't' || ch == 'T') tareScale();
    else if (ch == 'c' || ch == 'C') calibrateScaleInteractive();
    while (Serial.available()) Serial.read();
  }

  wifi_ensure_connected();

  uint32_t now = millis();
  if (now - last_ms >= PERIOD_MS) {
    last_ms += PERIOD_MS;

    long raw = readRawBlocking();
    float kg_f = filteredKgFromRaw(raw);

    zeroTrackingUpdate(raw, kg_f);

    udp_sender_send_weight(kg_f);
  }
}
