from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Timed:
    ok: bool
    ms: float


def now_ms() -> float:
    return time.perf_counter() * 1000.0


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write_json(path: str, data: Any) -> None:
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def clamp(n: int, lo: int, hi: int) -> int:
    return max(lo, min(hi, n))
