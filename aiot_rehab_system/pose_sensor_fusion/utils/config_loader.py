from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

import yaml


def load_yaml_config(path: str) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Config file not found: {p}")

    with p.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if not isinstance(cfg, dict):
        raise ValueError("YAML root must be a mapping (dict).")

    return cfg
