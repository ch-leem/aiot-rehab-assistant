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
    "상체1": "팔을 편 상태로 팔을 들어주세요.",
    "상체2": "어깨가 틀어지거나 팔꿈치가 굽히지 않도록 주의해주세요.",
    "상체3": "반동을 사용하여 팔을 들지 않도록 주의해주세요.",
    "시작신호": "삼 이 일 시작 신호에 맞춰 운동을 시작합니다.",
    "하체1": "아픈 발을 발판 위에 올려주세요.",
    "하체2": "반대쪽 발 뒷꿈치를 들며 아픈 발에 체중을 실어주세요.",
    "하체3": "반대쪽 발이 흔들리거나 상체 골반이 기울어지지 않도록 주의해주세요."
    
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
            "instruction": (
                "당신은 병원 재활 시스템의 음성 안내자입니다.\n"
                "차분하고 따뜻하며 전문적인 톤으로 말하세요.\n"
                "환자를 격려하되 과장되거나 들뜨지 않도록 합니다.\n"
                "말하는 속도는 평소보다 약간 느리게,\n"
                "의료진이 옆에서 부드럽게 안내하는 느낌으로 말하세요.\n"
            ),
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
