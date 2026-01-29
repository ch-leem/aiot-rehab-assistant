#include <Arduino.h>
#include <EEPROM.h>

/*
  Stepper: 28BYJ-48 + ULN2003 (Full-step, 2-phase ON)
  IN1 -> D8, IN2 -> D9, IN3 -> D10, IN4 -> D11
  Home switch -> D2 (INPUT_PULLUP, pressed=LOW)

  Serial (Jetson): text commands, newline terminated
*/

#define IN1 8
#define IN2 9
#define IN3 10
#define IN4 11

#define HOME_SW_PIN 2

// -----------------------
// Stepper tuning parameters
// -----------------------
float MAX_SPEED_SPS   = 650.0f;
float MIN_SPEED_SPS   = 40.0f;
float MAX_ACCEL_SPS2  = 800.0f;
float MAX_JERK_SPS3   = 6000.0f;
const int DIR_FLIP_PHASE = 1;
const float STOP_MARGIN_STEPS = 8.0f;

// Stepper travel limits
long STEP_MIN_POS = 0;
long STEP_MAX_POS = +17500;

// -----------------------
// Homing parameters
// -----------------------
const int HOME_DIR_LOGICAL = -1;
float HOME_SPEED_SPS = 600.0f;
unsigned long HOME_DEBOUNCE_MS = 20;
unsigned long HOME_STEP_GUARD_US = 1200;

// -----------------------
// Stepper state
// -----------------------
long pos_steps = 0;
int phase = 0;

volatile long targetPos = 0;
volatile unsigned long T_us = 1000UL * 1000UL;
volatile bool moving = false;

float v_cmd = 0.0f;
float a_cmd = 0.0f;
unsigned long last_ctrl_us = 0;
unsigned long next_step_us = 0;

enum HomeState : uint8_t { HOME_INIT, HOME_SEEK, HOME_DONE };
HomeState homeState = HOME_INIT;

unsigned long home_next_step_us = 0;
unsigned long home_pressed_since_ms = 0;

// -----------------------
// EEPROM config (optional)
// -----------------------
struct Config {
  long step_min, step_max;
  uint32_t magic;
};
const uint32_t CFG_MAGIC = 0xC0FFEE03; // (servo 제거 버전)
const int EEPROM_ADDR = 0;

// -----------------------
// Utils
// -----------------------
static inline float clampf(float x, float lo, float hi) {
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}
static inline long clampl(long x, long lo, long hi) {
  if (x < lo) return lo;
  if (x > hi) return hi;
  return x;
}
static inline bool homeSwitchPressed() {
  return (digitalRead(HOME_SW_PIN) == LOW);
}

// Full-step pattern: (1&2)->(2&3)->(3&4)->(4&1)
static inline void writePhase(int p) {
  switch (p & 3) {
    case 0:
      digitalWrite(IN1, HIGH); digitalWrite(IN2, HIGH);
      digitalWrite(IN3, LOW);  digitalWrite(IN4, LOW);
      break;
    case 1:
      digitalWrite(IN1, LOW);  digitalWrite(IN2, HIGH);
      digitalWrite(IN3, HIGH); digitalWrite(IN4, LOW);
      break;
    case 2:
      digitalWrite(IN1, LOW);  digitalWrite(IN2, LOW);
      digitalWrite(IN3, HIGH); digitalWrite(IN4, HIGH);
      break;
    case 3:
      digitalWrite(IN1, HIGH); digitalWrite(IN2, LOW);
      digitalWrite(IN3, LOW);  digitalWrite(IN4, HIGH);
      break;
  }
}

// Apply DIR_FLIP only to PHASE. pos_steps follows logical direction.
static inline void stepOnce(int dir_logical) {
  int dir_phase = dir_logical * DIR_FLIP_PHASE;

  phase += (dir_phase > 0) ? 1 : -1;
  phase &= 3;
  writePhase(phase);

  pos_steps += (dir_logical > 0) ? 1 : -1;
}

// -----------------------
// Stepper command handling
// -----------------------
// - 이동 중(MOVE 중) 새 MOVE가 오면 v_cmd/a_cmd/next_step_us를 리셋하지 않음 -> 끊김 없이 목적지만 변경
void setCommand(long newTargetAbs, unsigned long duration_ms) {
  newTargetAbs = clampl(newTargetAbs, STEP_MIN_POS, STEP_MAX_POS);

  unsigned long now = micros();
  bool wasMoving = moving;

  targetPos = newTargetAbs;
  T_us = (duration_ms == 0) ? 1UL : (duration_ms * 1000UL);

  moving = (targetPos != pos_steps);

  if (!wasMoving) {
    // 정지 상태에서 출발
    v_cmd = 0.0f;
    a_cmd = 0.0f;
    next_step_us = now;
  } else {
    // 이동 중 리타겟: 속도/가속/스텝 타이밍 유지
    long err_i = (long)targetPos - pos_steps;
    if ((err_i > 0 && v_cmd < 0) || (err_i < 0 && v_cmd > 0)) {
      a_cmd = 0.0f; // 급반전 시 가속만 리셋(선택)
    }
  }

  last_ctrl_us = now;

  Serial.print("CMD MOVE target=");
  Serial.print(targetPos);
  Serial.print(" hintT(ms)=");
  Serial.print(duration_ms);
  Serial.println(wasMoving ? " (retarget)" : " (start)");
}

void stopMotion() {
  moving = false;
  v_cmd = 0.0f;
  a_cmd = 0.0f;
  targetPos = pos_steps;
  Serial.println("CMD STOP");
}

void restartHoming() {
  moving = false;
  v_cmd = 0; a_cmd = 0;
  homeState = HOME_INIT;
  Serial.println("CMD HOME (restart)");
}

// -----------------------
// Stepper motion update
// -----------------------
void updateMotion() {
  if (!moving) return;

  unsigned long now = micros();
  float dt = (now - last_ctrl_us) * 1e-6f;
  if (dt < 0.0005f) dt = 0.0005f;
  last_ctrl_us = now;

  long err_i = (long)targetPos - pos_steps;
  if (err_i == 0) {
    moving = false;
    Serial.print("Done. pos=");
    Serial.println(pos_steps);
    return;
  }

  float err = (float)err_i;
  float dist = fabsf(err);

  float T_s = (float)T_us * 1e-6f;
  float v_hint = (T_s > 1e-4f) ? (dist / T_s) : MAX_SPEED_SPS;
  float v_cruise = clampf(v_hint, 0.0f, MAX_SPEED_SPS);

  float v_stop = sqrtf(2.0f * MAX_ACCEL_SPS2 * dist);
  float v_mag_des = fminf(v_cruise, v_stop);

  bool can_keep_min = (v_stop > (MIN_SPEED_SPS + STOP_MARGIN_STEPS));
  if (can_keep_min) {
    if (v_mag_des < MIN_SPEED_SPS) v_mag_des = MIN_SPEED_SPS;
  } else {
    if (v_mag_des > v_stop) v_mag_des = v_stop;
  }

  float v_des = (err > 0) ? +v_mag_des : -v_mag_des;

  float a_des = (v_des - v_cmd) / dt;
  a_des = clampf(a_des, -MAX_ACCEL_SPS2, +MAX_ACCEL_SPS2);

  float da_max = MAX_JERK_SPS3 * dt;
  float da = clampf(a_des - a_cmd, -da_max, +da_max);
  a_cmd += da;

  v_cmd += a_cmd * dt;
  v_cmd = clampf(v_cmd, -MAX_SPEED_SPS, +MAX_SPEED_SPS);

  float speed = fabsf(v_cmd);
  if (speed < 1.0f) speed = 1.0f;
  unsigned long interval_us = (unsigned long)(1000000.0f / speed);

  if ((long)(now - next_step_us) >= 0) {
    int dir = (v_cmd >= 0.0f) ? +1 : -1;

    // 안전: v_cmd 방향이 오차 부호랑 어긋나면 오차 방향으로 강제
    if ((dir > 0 && err_i < 0) || (dir < 0 && err_i > 0)) {
      dir = (err_i > 0) ? +1 : -1;
    }

    long nextPos = pos_steps + ((dir > 0) ? 1 : -1);
    if (nextPos < STEP_MIN_POS || nextPos > STEP_MAX_POS) {
      stopMotion();
      Serial.println("WARN: step limit reached, stopping");
      return;
    }

    stepOnce(dir);
    next_step_us = now + interval_us;
  }
}

// -----------------------
// Homing update (non-blocking)
// -----------------------
void updateHoming() {
  unsigned long now_us = micros();
  unsigned long now_ms = millis();

  switch (homeState) {
    case HOME_INIT: {
      if (homeSwitchPressed()) {
        pos_steps = 0;
        targetPos = 0;
        moving = false;
        v_cmd = 0; a_cmd = 0;
        Serial.println("Home already pressed. pos=0");
        homeState = HOME_DONE;
        return;
      }
      home_next_step_us = now_us;
      home_pressed_since_ms = 0;
      Serial.println("Homing: seeking - direction...");
      homeState = HOME_SEEK;
      return;
    }
    case HOME_SEEK: {
      bool pressed = homeSwitchPressed();

      if (pressed) {
        if (home_pressed_since_ms == 0) home_pressed_since_ms = now_ms;
        if ((now_ms - home_pressed_since_ms) >= HOME_DEBOUNCE_MS) {
          pos_steps = 0;
          targetPos = 0;
          moving = false;
          v_cmd = 0; a_cmd = 0;
          Serial.println("Homing complete. pos=0");
          homeState = HOME_DONE;
          return;
        }
      } else {
        home_pressed_since_ms = 0;
      }

      float speed = HOME_SPEED_SPS;
      if (speed < 1.0f) speed = 1.0f;
      unsigned long interval_us = (unsigned long)(1000000.0f / speed);
      if (interval_us < HOME_STEP_GUARD_US) interval_us = HOME_STEP_GUARD_US;

      if ((long)(now_us - home_next_step_us) >= 0) {
        stepOnce(HOME_DIR_LOGICAL);
        home_next_step_us = now_us + interval_us;
      }
      return;
    }
    case HOME_DONE:
    default:
      return;
  }
}

// -----------------------
// Config save/load
// -----------------------
void saveConfig() {
  Config c;
  c.step_min = STEP_MIN_POS;
  c.step_max = STEP_MAX_POS;
  c.magic = CFG_MAGIC;
  EEPROM.put(EEPROM_ADDR, c);
  Serial.println("CFG SAVED");
}

void loadConfig() {
  Config c;
  EEPROM.get(EEPROM_ADDR, c);
  if (c.magic != CFG_MAGIC) {
    Serial.println("CFG not found (using defaults)");
    return;
  }
  STEP_MIN_POS = c.step_min;
  STEP_MAX_POS = c.step_max;
  Serial.println("CFG LOADED");
}

// -----------------------
// Serial command parser
// -----------------------
void printHelp() {
  Serial.println("Commands:");
  Serial.println("  HOME");
  Serial.println("  MOVE <abs_steps> <time_ms>");
  Serial.println("  STOP");
  Serial.println("  POS?");
  Serial.println("  LIMIT <min_steps> <max_steps>");
  Serial.println("  SAVE | LOAD | HELP");
}

void handleLine(String line) {
  line.trim();
  if (line.length() == 0) return;

  char cmd[16] = {0};
  long a=0, b=0;

  if (sscanf(line.c_str(), "%15s %ld %ld", cmd, &a, &b) >= 1) {
    for (int i=0; cmd[i]; i++) cmd[i] = toupper(cmd[i]);

    if (!strcmp(cmd, "MOVE")) {
      if (sscanf(line.c_str(), "%*s %ld %ld", &a, &b) == 2) setCommand((long)a, (unsigned long)b);
      else Serial.println("ERR: MOVE <abs_steps> <time_ms>");
      return;
    }
    if (!strcmp(cmd, "LIMIT")) {
      if (sscanf(line.c_str(), "%*s %ld %ld", &a, &b) == 2) {
        STEP_MIN_POS = (long)a;
        STEP_MAX_POS = (long)b;
        pos_steps = clampl(pos_steps, STEP_MIN_POS, STEP_MAX_POS);
        targetPos  = clampl(targetPos, STEP_MIN_POS, STEP_MAX_POS);
        Serial.print("OK LIMIT "); Serial.print(STEP_MIN_POS); Serial.print(" "); Serial.println(STEP_MAX_POS);
      } else Serial.println("ERR: LIMIT <min> <max>");
      return;
    }
    if (!strcmp(cmd, "HOME")) { restartHoming(); return; }
    if (!strcmp(cmd, "STOP")) { stopMotion(); return; }
    if (!strcmp(cmd, "POS?")) { Serial.print("POS "); Serial.println(pos_steps); return; }
    if (!strcmp(cmd, "HELP")) { printHelp(); return; }
    if (!strcmp(cmd, "SAVE")) { saveConfig(); return; }
    if (!strcmp(cmd, "LOAD")) { loadConfig(); return; }

    Serial.println("ERR: unknown cmd (type HELP)");
  }
}

void readSerialCommand() {
  if (!Serial.available()) return;
  String line = Serial.readStringUntil('\n');
  handleLine(line);
}

// -----------------------
void setup() {
  Serial.begin(115200);

  pinMode(IN1, OUTPUT);
  pinMode(IN2, OUTPUT);
  pinMode(IN3, OUTPUT);
  pinMode(IN4, OUTPUT);

  pinMode(HOME_SW_PIN, INPUT_PULLUP);

  writePhase(phase);

  // load config if exists
  loadConfig();

  Serial.println("Ready (Stepper only). Type HELP.");
  Serial.println("Boot homing starts automatically.");
}

void loop() {
  readSerialCommand();

  if (homeState != HOME_DONE) updateHoming();
  else                        updateMotion();
}
