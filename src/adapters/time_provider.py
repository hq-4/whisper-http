from __future__ import annotations

import time

from src.usecases.ports import Clock


class SystemClock(Clock):
    def monotonic(self) -> float:
        return time.monotonic()
