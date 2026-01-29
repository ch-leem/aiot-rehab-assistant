"""
입력으로 운동 상태를 제어하는 TTS 시스템

TTS 입력 코드:
R -> release 단계 (내려주세요 / 힘 빼주세요)
F1~F7 -> 실패 피드백
T -> 완벽합니다
S -> 시작
q -> 전체 종료
"""

import time
import tempfile
import platform
import subprocess
import yaml
from typing import Optional

import requests

FAILURE_MAP = {
    "F1": "수동 움직임입니다, 근활성 부족이에요",
    "F2": "보상 동작입니다, 자세가 무너지고 있어요",
    "F3": "속도 오류입니다, 반동이나 급가속을 줄여주세요",
    "F4": "가동 범위가 부족해요, 근력이나 가동성을 점검해주세요",
    "F5": "불안정하거나 떨림이 있어요, 신경 제어를 신경써주세요",
    "F6": "비대칭이에요, 한쪽만 쓰고 있지 않은지 확인해주세요",
    "F7": "피로가 누적된 것 같아요, 반복 과부하를 줄여주세요",
}

PERFECT_TEXT = "완벽합니다"

UPPER_START_TEXT = "상체 운동을 시작합니다"
LOWER_START_TEXT = "하체 운동을 시작합니다"

UPPER_TRY_TEXT = "8초간 양팔을 최대한 들어주세요"
LOWER_TRY_TEXT = "8초간 다리에 힘을 주세요"

UPPER_TRY_END_TEXT = "팔을 내려주세요"
LOWER_TRY_END_TEXT = "다리 힘을 빼주세요"

END_TEXT = "운동을 종료합니다 고생하셨습니다"

def play_audio_file(filepath: str) -> None:
    system = platform.system().lower()
    try:
        if "darwin" in system:
            subprocess.run(["afplay", filepath], check=False)
        elif "linux" in system:
            subprocess.run(["aplay", filepath], check=False)
        elif "windows" in system:
            ps = (
                "Add-Type -AssemblyName presentationCore;"
                f"$p='{filepath}';"
                "$mplayer = New-Object System.Windows.Media.MediaPlayer;"
                "$mplayer.Open([uri]$p);"
                "$mplayer.Volume=1.0;"
                "$mplayer.Play();"
                "Start-Sleep -Milliseconds 200;"
                "while($mplayer.NaturalDuration.HasTimeSpan -eq $false){Start-Sleep -Milliseconds 50};"
                "while($mplayer.Position -lt $mplayer.NaturalDuration.TimeSpan){Start-Sleep -Milliseconds 100}"
            )
            subprocess.run(["powershell", "-Command", ps], check=False)
    except Exception:
        pass


class GmsTTS:
    def __init__(self, gms_key: str, gms_url: str):
        self.gms_key = gms_key
        self._url = gms_url

    def speak(self, text: str) -> None:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.gms_key}",
        }
        payload = {
            "model": "gpt-4o-mini-tts",
            "input": text,
            "voice": "nova",
            "response_format": "mp3",
        }

        r = requests.post(self._url, headers=headers, json=payload, timeout=30)
        r.raise_for_status()

        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            f.write(r.content)
            play_audio_file(f.name)


class ExerciseSession:
    def __init__(self, gms_key: str, gms_url: str, ex_type: int, sets_count: int = 10):
        self.tts = GmsTTS(gms_key, gms_url)
        self.ex_type = ex_type
        self.sets_count = sets_count
        self.cur_set = 1

    def _start_text(self):
        return UPPER_START_TEXT if self.ex_type == 1 else LOWER_START_TEXT

    def _hold_text(self):
        return UPPER_TRY_TEXT if self.ex_type == 1 else LOWER_TRY_TEXT

    def _release_text(self):
        return UPPER_TRY_END_TEXT if self.ex_type == 1 else LOWER_TRY_END_TEXT

    def run(self):
        self.tts.speak(self._start_text())
        print("입력: H(유지) R(내리기) F1~F7 T N q")

        while self.cur_set <= self.sets_count:
            print(f"\n세트 {self.cur_set}/{self.sets_count}")
            raw = input(">> ").strip().upper()

            if raw == "Q":
                break
            elif raw == "R":
                self.tts.speak(self._release_text())
            elif raw == "T":
                self.tts.speak(PERFECT_TEXT)
            elif raw == "S":
                self.tts.speak(self._hold_text())
                self.cur_set += 1
            elif raw in FAILURE_MAP:
                self.tts.speak(FAILURE_MAP[raw])
            else:
                print("알 수 없는 코드")

        self.tts.speak(END_TEXT)


def main():

    with open("./gms.yaml", "r") as f:
        config = yaml.safe_load(f)

    GMS_KEY = config["GMS"]  # 여기에 키
    GMS_URL = config["GMS_URL"]

    ex_type = int(input("운동 선택 (1:상체, 2:하체): "))
    session = ExerciseSession(GMS_KEY, GMS_URL, ex_type)
    session.run()


if __name__ == "__main__":
    main()
