"""The gathering loop as an explicit state machine.

States:
    SETUP          pick up gathering tools at the deposit spot
    SEEK_RESOURCE  read the Alt overlay, locate a tree/rock
    NAVIGATE       walk toward it, avoiding/escaping obstacles
    GATHER         swing Mouse 1 N times to break the node
    COLLECT        press F a few times to vacuum the dropped bundles
    CHECK_CAPACITY read the Alt capacity widget; full -> RETURN, else SEEK
    RETURN         navigate back to the deposit spot
    DEPOSIT        unload, then loop back to SEEK_RESOURCE
    STOPPED        emergency stop / fatal error

Each state returns the next state, so the main loop stays trivial.
"""
from __future__ import annotations

import enum
import time

from .capture import ScreenCapture
from .controls import Controls
from .navigation import Navigator
from .vision import OCRBackend, find_label, read_capacity


class State(enum.Enum):
    SETUP = "SETUP"
    SEEK_RESOURCE = "SEEK_RESOURCE"
    NAVIGATE = "NAVIGATE"
    GATHER = "GATHER"
    COLLECT = "COLLECT"
    CHECK_CAPACITY = "CHECK_CAPACITY"
    RETURN = "RETURN"
    DEPOSIT = "DEPOSIT"
    STOPPED = "STOPPED"


class GatherBot:
    def __init__(self, cfg, capture, controls, navigator, ocr, advisor=None):
        self.cfg = cfg
        self.cap: ScreenCapture = capture
        self.ctrl: Controls = controls
        self.nav: Navigator = navigator
        self.ocr: OCRBackend = ocr
        self.advisor = advisor

        self.state = State.SETUP
        self._failed_reads = 0
        self._nav_target = "resource"  # 'resource' or 'deposit'
        self._approach_tries = 0

    # ---- perception helpers ---------------------------------------------------
    def _read_overlay(self):
        """Hold Alt, capture, OCR. Returns (frame, detections)."""
        self.ctrl.hold_alt()
        time.sleep(self.cfg.timings["alt_settle_s"])
        frame = self.cap.grab()
        self.ctrl.release_alt()
        dets = self.ocr.read(frame)
        return frame, dets

    def _read_capacity(self):
        self.ctrl.hold_alt()
        time.sleep(self.cfg.timings["alt_settle_s"])
        frame = self.cap.grab()
        crop = self.cap.crop(frame, self.cfg.capacity["region"])
        self.ctrl.release_alt()
        return read_capacity(self.ocr, crop, self.cfg.capacity["pattern"])

    def _ask_advisor(self, goal: str):
        if not self.advisor:
            return None
        frame = self.cap.grab()
        return self.advisor.advise(frame, goal=goal)

    # ---- states ---------------------------------------------------------------
    def setup(self) -> State:
        """At the deposit spot: locate and pick up the gathering tools."""
        print("[setup] locating gathering tools...")
        _, dets = self._read_overlay()
        tool = find_label(dets, self.cfg.labels["tool_pickup"])
        if tool is not None:
            self.nav.center_target(tool)
            self.nav.walk_forward()
            self.ctrl.interact_once()  # F to pick up tools
            print("[setup] tools acquired (or attempted). Beginning gather cycle.")
            self._nav_target = "resource"
            return State.SEEK_RESOURCE
        # Tools not seen — turn to scan, then retry. Bail to SEEK after a while.
        self._failed_reads += 1
        if self._failed_reads > 6:
            print("[setup] couldn't find tools; assuming already equipped.")
            self._failed_reads = 0
            return State.SEEK_RESOURCE
        self.nav.scan_turn()
        return State.SETUP

    def seek_resource(self) -> State:
        labels = (
            self.cfg.labels["resource_targets"]
            if self._nav_target == "resource"
            else self.cfg.labels["deposit_point"]
        )
        frame, dets = self._read_overlay()
        target = find_label(dets, labels)
        if target is not None:
            self._failed_reads = 0
            self._current_target = target
            return State.NAVIGATE if self._nav_target == "resource" else State.RETURN

        # Nothing found locally.
        self._failed_reads += 1
        if (
            self.advisor
            and self._failed_reads >= self.cfg.advisor["trigger_after_failed_reads"]
        ):
            advice = self._ask_advisor(self._nav_target)
            if advice:
                print(f"[advisor] {advice.action} ({advice.reason})")
                self._apply_advice(advice)
                self._failed_reads = 0
                return self.state
        self.nav.scan_turn()
        return State.SEEK_RESOURCE if self._nav_target == "resource" else State.RETURN

    def navigate(self) -> State:
        """Walk toward self._current_target, re-reading the overlay periodically."""
        target = getattr(self, "_current_target", None)
        if target is None:
            return State.SEEK_RESOURCE

        if not self.nav.center_target(target):
            return State.NAVIGATE  # still turning to face it

        before = self.cap.grab()
        self.nav.walk_forward()
        after = self.cap.grab()
        moving = self.nav.step_toward(before, after)

        if self.nav.is_stuck():
            print("[navigate] stuck — running unstick routine")
            self.nav.unstick()
            if self.advisor:
                advice = self._ask_advisor("resource")
                if advice:
                    self._apply_advice(advice)
            return State.SEEK_RESOURCE

        # Re-acquire the target; if it's now large/close we assume we're in range.
        _, dets = self._read_overlay()
        target = find_label(dets, self.cfg.labels["resource_targets"])
        if target is None:
            # Lost sight of it — could be right on top of it. Try to gather.
            self._approach_tries += 1
            if self._approach_tries >= 3:
                self._approach_tries = 0
                return State.GATHER
            return State.SEEK_RESOURCE
        self._current_target = target
        # Heuristic "close enough": label near vertical center of the screen.
        frame_h = self.cap.monitor["height"]
        if target.cy > frame_h * 0.4:
            self._approach_tries = 0
            return State.GATHER
        return State.NAVIGATE

    def gather(self) -> State:
        print("[gather] swinging")
        self.ctrl.swing(
            self.cfg.gather["swings_per_node"], self.cfg.gather["swing_interval_s"]
        )
        return State.COLLECT

    def collect(self) -> State:
        print("[collect] picking up bundles")
        self.ctrl.collect(
            self.cfg.gather["collect_presses"], self.cfg.gather["collect_interval_s"]
        )
        return State.CHECK_CAPACITY

    def check_capacity(self) -> State:
        cap = self._read_capacity()
        if cap is None:
            print("[capacity] unreadable — continuing to gather")
            return State.SEEK_RESOURCE
        current, maximum = cap
        ratio = current / maximum
        print(f"[capacity] {current}/{maximum} ({ratio:.0%})")
        if ratio >= self.cfg.capacity["full_threshold"]:
            print("[capacity] full — heading back to deposit")
            self._nav_target = "deposit"
            return State.SEEK_RESOURCE  # seek will route to RETURN for the deposit goal
        return State.SEEK_RESOURCE

    def ret(self) -> State:
        """Navigate to the deposit point (reuses target acquired in seek)."""
        target = getattr(self, "_current_target", None)
        if target is None:
            return State.SEEK_RESOURCE
        if not self.nav.center_target(target):
            return State.RETURN
        before = self.cap.grab()
        self.nav.walk_forward()
        after = self.cap.grab()
        self.nav.step_toward(before, after)
        if self.nav.is_stuck():
            self.nav.unstick()
            return State.SEEK_RESOURCE
        _, dets = self._read_overlay()
        dep = find_label(dets, self.cfg.labels["deposit_point"])
        if dep is None:
            return State.DEPOSIT  # likely arrived
        self._current_target = dep
        frame_h = self.cap.monitor["height"]
        if dep.cy > frame_h * 0.4:
            return State.DEPOSIT
        return State.RETURN

    def deposit(self) -> State:
        print("[deposit] unloading")
        # Open/interact with the deposit and dump. Game-specific; F a few times.
        self.ctrl.collect(self.cfg.gather["collect_presses"], 0.5)
        self._nav_target = "resource"
        return State.SEEK_RESOURCE

    # ---- advisor glue ---------------------------------------------------------
    def _apply_advice(self, advice) -> None:
        if advice.action == "turn_left":
            self.ctrl.turn("left", pixels=200)
        elif advice.action == "turn_right":
            self.ctrl.turn("right", pixels=200)
        elif advice.action == "move":
            # Steer roughly toward the reported direction, then step forward.
            if advice.target_direction < -0.2:
                self.ctrl.turn("left", pixels=int(abs(advice.target_direction) * 200))
            elif advice.target_direction > 0.2:
                self.ctrl.turn("right", pixels=int(advice.target_direction * 200))
            self.nav.walk_forward()
        elif advice.action == "gather":
            self.state = State.GATHER
        elif advice.action == "deposit":
            self.state = State.DEPOSIT

    # ---- dispatch -------------------------------------------------------------
    def tick(self) -> State:
        dispatch = {
            State.SETUP: self.setup,
            State.SEEK_RESOURCE: self.seek_resource,
            State.NAVIGATE: self.navigate,
            State.GATHER: self.gather,
            State.COLLECT: self.collect,
            State.CHECK_CAPACITY: self.check_capacity,
            State.RETURN: self.ret,
            State.DEPOSIT: self.deposit,
        }
        handler = dispatch.get(self.state)
        if handler is None:
            return State.STOPPED
        self.state = handler()
        return self.state
