import json
import os
import time
from typing import Any, Dict, Optional

class JsonLogger:
    """
    NDJSON logger (one JSON per line).
    """
    def __init__(self, log_dir: str, prefix: str = "pose_imu", ext: str = "ndjson"):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, time.strftime(f"{prefix}_%Y%m%d_%H%M%S.{ext}"))
        self._f = open(self.path, "w", buffering=1)

    def write_frame(self, frame_obj: Dict[str, Any]):
        self._f.write(json.dumps(frame_obj, ensure_ascii=False) + "\n")

    def close(self):
        try:
            self._f.flush()
            self._f.close()
        except Exception:
            pass
