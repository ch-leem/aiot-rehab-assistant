import os
import yaml
import requests
from dataclasses import dataclass
import re

def safe_text(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"\s+", "_", text)              
    text = re.sub(r"[^0-9a-z가-힣_]+", "", text)    
    text = re.sub(r"_+", "_", text)                
    return text[:80]                               


mp3_map = {
    "F_SH_FLEX": "팔을 더 들어주세요.",
    "F_EL_EXT": "팔을 편 상태로 운동해주세요.",
    "F_TR_TILT": "허리를 펴주세요.",
    "F_SH_HOR": "어깨를 맞춰주세요.",
    "F_ACCEL": "팔을 천천히 들어주세요.",
    "F_PR_LOAD": "발에 힘을 더 주세요.",
    "F_PL_HOR": "골반을 맞춰주세요.",
    "F_ANK_STB": "반대쪽 발에 발목을 고정해주세요.",
    "F_ELSE": "예외 발생 예외 발생",
    "T": "잘하셨어요.",
    "3": "삼",
    "2": "이",
    "1": "일",
    "시작": "시작~",
}


@dataclass
class GmsTTS:
    gms_key: str
    gms_url: str

    def synth_mp3(self, text: str) -> bytes:
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

        r = requests.post(self.gms_url, headers=headers, json=payload, timeout=60)
        r.raise_for_status()
        return r.content


def main():
    with open("./gms.yaml", "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    tts = GmsTTS(config["GMS"], config["GMS_URL"])

    out_dir = "./tts_mp3"
    os.makedirs(out_dir, exist_ok=True)

    for code, text in mp3_map.items():
        txt = safe_text(text)
        path = os.path.join(out_dir, f"{code}_{txt}.mp3")

        if os.path.exists(path) and os.path.getsize(path) > 0:
            print(f"[SKIP] {code}_{txt}.mp3 이미 존재")
            continue

        try:
            audio = tts.synth_mp3(text)
            with open(path, "wb") as f:
                f.write(audio)
            print(f"[OK] {code}_{txt}.mp3 생성")
        except Exception as e:
            print(f"[FAIL] {code}_{txt} 생성 실패: {e}")


if __name__ == "__main__":
    main()
