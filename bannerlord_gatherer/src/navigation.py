"""Heuristic, obstacle-aware navigation toward an on-screen target.

Pure screen-reading can't build a real map, so this uses two cheap signals:
  1. Where the target's Alt-label sits horizontally  -> which way to turn.
  2. Frame-to-frame pixel difference while moving      -> "am I stuck?".

When stuck, we run an unstick routine (back up, turn, strafe). This is good
enough for open gathering fields; it is NOT a substitute for real pathfinding
in cluttered terrain. The Claude advisor can be consulted when this gives up.
"""
from __future__ import annotations

import time

import cv2
import numpy as np

from .controls import Controls
from .vision import Detection


class Navigator:
    def __init__(self, controls: Controls, nav_cfg: dict, frame_width: int):
        self.c = controls
        self.cfg = nav_cfg
        self.frame_width = frame_width
        self._stuck_counter = 0

    @staticmethod
    def frame_diff(a: np.ndarray, b: np.ndarray) -> float:
        """Mean absolute difference between two frames (downsized for speed)."""
        ga = cv2.cvtColor(cv2.resize(a, (160, 90)), cv2.COLOR_BGR2GRAY)
        gb = cv2.cvtColor(cv2.resize(b, (160, 90)), cv2.COLOR_BGR2GRAY)
        return float(np.mean(np.abs(ga.astype(np.int16) - gb.astype(np.int16))))

    def center_target(self, target: Detection) -> bool:
        """Turn toward the target. Returns True if it's roughly centered."""
        frac = target.cx / self.frame_width
        lo, hi = self.cfg["center_band"]
        if frac < lo:
            self.c.turn("left", pixels=80)
            return False
        if frac > hi:
            self.c.turn("right", pixels=80)
            return False
        return True

    def step_toward(self, prev_frame: np.ndarray, new_frame: np.ndarray) -> bool:
        """Walk forward one step. Returns True if movement was detected.

        Caller is responsible for capturing prev_frame before and new_frame
        after the forward movement.
        """
        diff = self.frame_diff(prev_frame, new_frame)
        if diff < self.cfg["stuck_frame_diff"]:
            self._stuck_counter += 1
        else:
            self._stuck_counter = 0
        return self._stuck_counter < self.cfg["stuck_checks_before_unstick"]

    def is_stuck(self) -> bool:
        return self._stuck_counter >= self.cfg["stuck_checks_before_unstick"]

    def walk_forward(self) -> None:
        self.c.move_forward(self.cfg["approach_step_s"])

    def unstick(self) -> None:
        """Back up, turn a random-ish direction, and strafe to escape an obstacle."""
        self.c.move_back(self.cfg["unstick_back_s"])
        direction = "left" if (int(time.time()) % 2 == 0) else "right"
        self.c.turn(direction, pixels=200)
        time.sleep(self.cfg["unstick_turn_s"])
        self.c.strafe(direction, self.cfg["unstick_back_s"])
        self._stuck_counter = 0

    def scan_turn(self) -> None:
        """No target visible: rotate in place to bring new objects into view."""
        self.c.turn("right", pixels=160)
        time.sleep(0.1)
