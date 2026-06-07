"""Input simulation for a DirectX game via pydirectinput.

pydirectinput emits hardware scancodes through SendInput, which Bannerlord (and
most DX titles) actually register — plain pyautogui keystrokes are frequently
ignored by the game's input layer.
"""
from __future__ import annotations

import random
import time

import pydirectinput

# Don't insert pydirectinput's default sleep after every call; we manage timing.
pydirectinput.PAUSE = 0.0
# Keep the library's own corner failsafe off — we use our own F9 emergency stop.
pydirectinput.FAILSAFE = False


class Controls:
    def __init__(self, keys: dict, jitter_pct: float = 0.0):
        self.k = keys
        # +/- randomness applied to every sleep so timings aren't metronomic.
        self.jitter_pct = max(0.0, float(jitter_pct))

    def _j(self, duration: float) -> float:
        """Apply symmetric jitter to a duration."""
        if self.jitter_pct <= 0.0:
            return duration
        return duration * (1.0 + random.uniform(-self.jitter_pct, self.jitter_pct))

    def _sleep(self, duration: float) -> None:
        time.sleep(max(0.0, self._j(duration)))

    # ---- low-level key helpers ------------------------------------------------
    def tap(self, key: str, duration: float = 0.05) -> None:
        pydirectinput.keyDown(key)
        self._sleep(duration)
        pydirectinput.keyUp(key)

    def key_down(self, key: str) -> None:
        pydirectinput.keyDown(key)

    def key_up(self, key: str) -> None:
        pydirectinput.keyUp(key)

    def press_n(self, key: str, n: int, interval: float) -> None:
        for _ in range(n):
            self.tap(key)
            self._sleep(interval)

    # ---- mouse ----------------------------------------------------------------
    def click(self, button: str = "left", duration: float = 0.08) -> None:
        pydirectinput.mouseDown(button=button)
        self._sleep(duration)
        pydirectinput.mouseUp(button=button)

    def move_mouse_rel(self, dx: int, dy: int) -> None:
        """Relative mouse move — used to turn the camera/character."""
        pydirectinput.moveRel(dx, dy, relative=True)

    # ---- semantic movement ----------------------------------------------------
    def move_forward(self, duration: float) -> None:
        self.key_down(self.k["forward"])
        self._sleep(duration)
        self.key_up(self.k["forward"])

    def move_back(self, duration: float) -> None:
        self.key_down(self.k["back"])
        self._sleep(duration)
        self.key_up(self.k["back"])

    def strafe(self, direction: str, duration: float) -> None:
        key = self.k["left"] if direction == "left" else self.k["right"]
        self.key_down(key)
        self._sleep(duration)
        self.key_up(key)

    def turn(self, direction: str, pixels: int = 120) -> None:
        """Turn the camera left/right by nudging the mouse horizontally."""
        dx = -pixels if direction == "left" else pixels
        self.move_mouse_rel(dx, 0)

    def stop_all(self) -> None:
        for key in (self.k["forward"], self.k["back"], self.k["left"], self.k["right"]):
            try:
                pydirectinput.keyUp(key)
            except Exception:
                pass
        try:
            pydirectinput.keyUp(self.k["alt_inspect"])
        except Exception:
            pass

    # ---- high level actions ---------------------------------------------------
    def hold_alt(self) -> None:
        self.key_down(self.k["alt_inspect"])

    def release_alt(self) -> None:
        self.key_up(self.k["alt_inspect"])

    def swing(self, n: int, interval: float) -> None:
        """Swing the gathering tool n times with Mouse 1."""
        for _ in range(n):
            self.click(self.k["attack_button"])
            self._sleep(interval)

    def collect(self, n: int, interval: float) -> None:
        """Press the interact key (F) n times to pick up dropped bundles."""
        self.press_n(self.k["interact"], n, interval)

    def interact_once(self) -> None:
        self.tap(self.k["interact"])
