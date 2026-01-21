import json
from typing import Any, Dict, List


def load_data_payload(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def build_header_from_payload(payload: Dict[str, Any]) -> List[str]:
    header: List[str] = []

    base_fields = payload.get("base_fields", [])
    header.extend(base_fields)

    joints = payload.get("joints")
    if joints:
        n = int(joints["num_joints"])
        per = list(joints["fields_per_joint"])
        prefix = str(joints.get("prefix", "j"))

        for j in range(n):
            for f in per:
                header.append(f"{prefix}{j}_{f}")

    header.extend(payload.get("extra_fields", []))
    return header
