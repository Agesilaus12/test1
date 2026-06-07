"""Session pacing: a hard runtime cap plus periodic human-like breaks.

A single instance that logs on for a couple of hours, takes the odd break, and
then stops on its own looks far less like a script than one that runs an
identical loop forever. This module enforces that without you watching the clock.
"""
from __future__ import annotations

import random
import time


class SessionLimiter:
    def __init__(self, session_cfg: dict):
        self.max_runtime_s = float(session_cfg.get("max_runtime_min", 0)) * 60.0
        self.break_every = session_cfg.get("break_every_min", [25, 45])
        self.break_duration = session_cfg.get("break_duration_s", [40, 150])
        self._start = time.time()
        self._next_break_at = self._schedule_next_break()

    def _schedule_next_break(self) -> float:
        lo, hi = self.break_every
        return time.time() + random.uniform(lo, hi) * 60.0

    def expired(self) -> bool:
        """True once the configured max runtime has elapsed (0 = never)."""
        if self.max_runtime_s <= 0:
            return False
        return (time.time() - self._start) >= self.max_runtime_s

    def due_for_break(self) -> bool:
        return time.time() >= self._next_break_at

    def take_break(self) -> None:
        lo, hi = self.break_duration
        secs = random.uniform(lo, hi)
        mins = (time.time() - self._start) / 60.0
        print(f"[session] break for {secs:.0f}s (run-time so far {mins:.0f} min)")
        time.sleep(secs)
        self._next_break_at = self._schedule_next_break()

    def elapsed_min(self) -> float:
        return (time.time() - self._start) / 60.0
