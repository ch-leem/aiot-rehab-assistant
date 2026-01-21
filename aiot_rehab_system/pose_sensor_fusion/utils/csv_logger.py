import csv
import os
import time
from typing import List, Any


class CsvLogger:
    def __init__(self, log_dir: str, prefix: str = "pose_imu"):
        os.makedirs(log_dir, exist_ok=True)
        self.path = os.path.join(log_dir, time.strftime(f"{prefix}_%Y%m%d_%H%M%S.csv"))
        self._f = open(self.path, "w", newline="", buffering=1)
        self._w = csv.writer(self._f)
        self._header_written = False

    def write_header(self, header: List[str]):
        if not self._header_written:
            self._w.writerow(header)
            self._header_written = True

    def write_row(self, row: List[Any]):
        self._w.writerow(row)

    def close(self):
        try:
            self._f.flush()
            self._f.close()
        except Exception:
            pass
