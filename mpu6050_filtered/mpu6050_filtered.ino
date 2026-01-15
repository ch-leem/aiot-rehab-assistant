#include <Wire.h>
#include <I2Cdev.h>
#include <MPU6050.h>

MPU6050 mpu;

// ===== 샘플링 =====
static const float sampleHz = 100.0f;
static const uint32_t Ts_us = (uint32_t)(1000000.0f / sampleHz);
static const float dt = 1.0f / sampleHz;

// 플로터 출력
static const uint32_t plotHz = 50;
static const uint32_t plotPeriodUs = 1000000UL / plotHz;

// ===== 컴플리멘터리 필터 파라미터 =====
// alpha ↑ : 자이로 비중↑ (빠름, 드리프트↑), alpha ↓ : accel 비중↑ (안정, 둔함↑)
// 손동작용 추천 0.96~0.99
static const float alpha = 0.98f;

// ===== 상수 =====
static const float G = 9.80665f;

// ===== 정지 감지(튜닝) =====
static const float stillLinAccMs2 = 0.35f; // 선형가속도 크기(m/s^2) 기준
static const float stillGyroDps   = 6.0f;  // deg/s 기준
static const uint16_t stillHoldMs = 120;   // 이 시간 이상 정지면 speed=0

// ===== 속력 추정(EMA) =====
// 노이즈 바닥 제거(선형가속도 크기에서 빼줌)
static const float accDeadbandMs2 = 0.25f; // 0.15~0.5 튜닝

// tau * linAcc -> 목표 속력(m/s)로 만드는 시간상수(작을수록 민감)
static const float tau       = 0.20f; // 0.12~0.35
static const float emaRiseHz = 25.0f; // 올라갈 때 반응(클수록 빠름)
static const float emaFallHz = 40.0f; // 내려갈 때 반응(클수록 빠름)

uint32_t nextSample = 0;
uint32_t nextPlot   = 0;
uint32_t stillSinceMs = 0;

// 상태값(라디안)
float roll = 0.0f, pitch = 0.0f, yaw = 0.0f;

// 속력(스칼라)
float speed = 0.0f;

// 자이로 오프셋(간단 캘리브) - raw 단위(LSB)
float bgx = 0, bgy = 0, bgz = 0;

static inline float f_max(float a, float b) { return a > b ? a : b; }

void calibrateGyroBias(int samples = 300) {
  long sx = 0, sy = 0, sz = 0;

  for (int i = 0; i < samples; i++) {
    int16_t ax, ay, az, gx, gy, gz;
    mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
    sx += gx; sy += gy; sz += gz;
    delay(5);
  }

  bgx = (sx / (float)samples);
  bgy = (sy / (float)samples);
  bgz = (sz / (float)samples);
}

void setup() {
  Serial.begin(115200);
  delay(200);

  Wire.begin(D2, D1);        // NodeMCU: SDA=D2(GPIO4), SCL=D1(GPIO5)
  Wire.setClock(100000);     // 안정적으로 100k부터

  mpu.initialize();
  if (!mpu.testConnection()) {
    // 플로터에서 "0만" 보이게 하지 말고, 실패 시 멈춤
    Serial.println("MPU FAIL");
    while (1) delay(1000);
  }

  // range 고정(스케일 상수 16384, 131이 맞도록)
  mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_250);
  mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);

  // 자이로 바이어스 캘리브(가만히 둔 상태에서!)
  calibrateGyroBias(300);

  uint32_t now = micros();
  nextSample = now + Ts_us;
  nextPlot   = now + plotPeriodUs;

  // 플로터 채널 초기화(숫자 4개)
  Serial.println("0\t0\t0\t0");
}

void loop() {
  uint32_t now = micros();

  // ===== 100Hz 업데이트 =====
  if ((int32_t)(now - nextSample) >= 0) {
    nextSample += Ts_us;

    int16_t ax_i, ay_i, az_i, gx_i, gy_i, gz_i;
    mpu.getMotion6(&ax_i, &ay_i, &az_i, &gx_i, &gy_i, &gz_i);

    // accel: g 단위 (±2g)
    float ax_g = (float)ax_i / 16384.0f;
    float ay_g = (float)ay_i / 16384.0f;
    float az_g = (float)az_i / 16384.0f;

    // gyro: deg/s (±250dps) + 바이어스 제거
    float gx_dps = ((float)gx_i - bgx) / 131.0f;
    float gy_dps = ((float)gy_i - bgy) / 131.0f;
    float gz_dps = ((float)gz_i - bgz) / 131.0f;

    // accel 기반 roll/pitch (라디안)
    float rollAcc  = atan2f(ay_g, az_g);
    float pitchAcc = atan2f(-ax_g, sqrtf(ay_g * ay_g + az_g * az_g));

    // gyro 적분 (라디안)
    roll  += (gx_dps * DEG_TO_RAD) * dt;
    pitch += (gy_dps * DEG_TO_RAD) * dt;
    yaw   += (gz_dps * DEG_TO_RAD) * dt;

    // 컴플리멘터리 융합
    roll  = alpha * roll  + (1.0f - alpha) * rollAcc;
    pitch = alpha * pitch + (1.0f - alpha) * pitchAcc;

    // ===== 중력 제거(roll/pitch로 중력 벡터 계산) =====
    // g_sensor (g 단위) : yaw는 중력에 영향 없음
    float gx_g = -sinf(pitch);
    float gy_g =  sinf(roll) * cosf(pitch);
    float gz_g =  cosf(roll) * cosf(pitch);

    // 선형가속도 (g)
    float lax_g = ax_g - gx_g;
    float lay_g = ay_g - gy_g;
    float laz_g = az_g - gz_g;

    // 선형가속도 크기 (m/s^2)
    float linAcc = sqrtf(lax_g * lax_g + lay_g * lay_g + laz_g * laz_g) * G;

    // 데드밴드(노이즈 바닥 제거)
    linAcc = f_max(0.0f, linAcc - accDeadbandMs2);

    // 정지 감지(선형가속도 + 자이로)
    float gyroMagDps = sqrtf(gx_dps * gx_dps + gy_dps * gy_dps + gz_dps * gz_dps);
    bool still = (linAcc < stillLinAccMs2) && (gyroMagDps < stillGyroDps);

    uint32_t msNow = millis();
    if (still) {
      if (stillSinceMs == 0) stillSinceMs = msNow;
      if ((msNow - stillSinceMs) > stillHoldMs) {
        speed = 0.0f;  // ZUPT
      }
    } else {
      stillSinceMs = 0;
    }

    // 목표 속력(가상, m/s)
    float target = tau * linAcc;

    // EMA 계수(상승/하강 다르게)
    float kRise = 1.0f - expf(-emaRiseHz * dt);
    float kFall = 1.0f - expf(-emaFallHz * dt);
    float k = (target > speed) ? kRise : kFall;

    speed += k * (target - speed);
  }

  // ===== 플로터 출력(50Hz) =====
  now = micros();
  if ((int32_t)(now - nextPlot) >= 0) {
    nextPlot += plotPeriodUs;

    float rollDeg  = roll  * RAD_TO_DEG;
    float pitchDeg = pitch * RAD_TO_DEG;
    float yawDeg   = yaw   * RAD_TO_DEG;

    // speed yaw pitch roll
    Serial.print(speed);   Serial.print('\t');
    Serial.print(yawDeg);  Serial.print('\t');
    Serial.print(pitchDeg);Serial.print('\t');
    Serial.println(rollDeg);
  }
}
