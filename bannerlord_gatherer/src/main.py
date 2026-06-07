"""Entry point: wire everything together and run the gather loop with a safety stop.

Usage:
    python -m src.main                 # run with default config.yaml
    python -m src.main --config my.yaml
    python -m src.main --dry-run       # set up + read screen but send NO inputs

Press the emergency-stop hotkey (default F9) at any time to halt instantly.
"""
from __future__ import annotations

import argparse
import sys
import time

import keyboard

from .capture import ScreenCapture
from .config import load_config
from .controls import Controls
from .navigation import Navigator
from .session import SessionLimiter
from .state_machine import GatherBot, State
from .vision import OCRBackend


def build_bot(cfg, dry_run: bool):
    capture = ScreenCapture(cfg.screen["capture_region"])
    jitter = float(cfg.session.get("jitter_pct", 0.0)) if "session" in cfg else 0.0
    controls = Controls(cfg.keys, jitter_pct=jitter)
    if dry_run:
        # Replace every input method with a no-op logger.
        import types

        def noop(*a, **k):
            return None

        for name in dir(controls):
            if not name.startswith("_") and callable(getattr(controls, name)):
                setattr(controls, name, types.MethodType(lambda self, *a, **k: None, controls))
        print("[main] DRY RUN — no inputs will be sent.")

    navigator = Navigator(controls, cfg.navigation, cfg.screen["capture_region"]["width"])
    print("[main] loading OCR backend (first run downloads models)...")
    ocr = OCRBackend()

    advisor = None
    if cfg.advisor.get("enabled"):
        try:
            from .claude_advisor import ClaudeAdvisor

            advisor = ClaudeAdvisor(cfg.advisor)
            print("[main] Claude advisor enabled.")
        except Exception as exc:
            print(f"[main] advisor disabled ({exc}).")

    return GatherBot(cfg, capture, controls, navigator, ocr, advisor), controls, capture


def main(argv=None):
    parser = argparse.ArgumentParser(description="Bannerlord Online gathering bot")
    parser.add_argument("--config", default=None, help="path to config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="read screen but send no input")
    args = parser.parse_args(argv)

    cfg = load_config(args.config)
    bot, controls, capture = build_bot(cfg, args.dry_run)

    stop_key = cfg.keys["emergency_stop"]
    stopped = {"flag": False}

    def _stop():
        stopped["flag"] = True

    keyboard.add_hotkey(stop_key, _stop)

    session = SessionLimiter(cfg.session) if "session" in cfg else None
    print(f"[main] running. Press {stop_key.upper()} to stop. Starting in 3s — focus the game window.")
    time.sleep(3)

    try:
        while not stopped["flag"]:
            if session and session.expired():
                print(f"[session] reached max runtime ({session.elapsed_min():.0f} min) — stopping.")
                break
            if session and session.due_for_break():
                # Release everything before idling so we don't hold a key during the break.
                controls.stop_all()
                session.take_break()

            state = bot.tick()
            if state == State.STOPPED:
                break
            time.sleep(cfg.timings["loop_sleep_s"])
    except KeyboardInterrupt:
        pass
    finally:
        controls.stop_all()
        capture.close()
        print("\n[main] stopped — all keys released.")


if __name__ == "__main__":
    sys.exit(main())
