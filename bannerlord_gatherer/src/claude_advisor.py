"""Optional Claude vision advisor.

The local OCR/heuristics drive the loop. When they get stuck (no target found,
repeatedly blocked), we send a downscaled screenshot to Claude and ask a single,
structured question: "which way do I go, and what should I do?" This keeps the
AI in the loop for the hard perceptual judgement calls without paying API latency
on every frame.

Requires `pip install anthropic pillow` and ANTHROPIC_API_KEY in the environment.
"""
from __future__ import annotations

import base64
import io
import time
from typing import Literal, Optional

import numpy as np

try:
    from pydantic import BaseModel
except ImportError:  # pragma: no cover
    BaseModel = None  # type: ignore


# Structured answer we constrain Claude to return.
if BaseModel is not None:

    class Advice(BaseModel):
        action: Literal["move", "turn_left", "turn_right", "gather", "deposit", "wait"]
        # Horizontal hint: -1.0 = far left of screen, 0 = center, 1.0 = far right.
        target_direction: float
        reason: str


SYSTEM_PROMPT = (
    "You are a vision assistant for a resource-gathering character in the game "
    "Bannerlord Online. You receive a screenshot of the player's first/third-person "
    "view. The player gathers wood and stone by walking up to trees and rock nodes "
    "and harvesting them, then returns to a deposit point when full.\n"
    "Look at the image and decide the single best next action to make progress "
    "toward the nearest harvestable resource (or the deposit point if asked). "
    "Report the horizontal direction of that thing as target_direction in [-1, 1] "
    "(-1 hard left, 0 dead center, 1 hard right). Be decisive and concise."
)


class ClaudeAdvisor:
    def __init__(self, advisor_cfg: dict):
        if BaseModel is None:
            raise ImportError("pydantic is required for the Claude advisor (pip install pydantic).")
        import anthropic  # lazy import

        self.cfg = advisor_cfg
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self._last_call = 0.0

    def _encode(self, frame: np.ndarray) -> str:
        from PIL import Image

        img = Image.fromarray(frame[:, :, ::-1])  # BGR -> RGB
        target_w = int(self.cfg.get("downscale_width", 1024))
        if img.width > target_w:
            ratio = target_w / img.width
            img = img.resize((target_w, int(img.height * ratio)))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.standard_b64encode(buf.getvalue()).decode("utf-8")

    def cooled_down(self) -> bool:
        return (time.time() - self._last_call) >= float(self.cfg.get("cooldown_s", 5.0))

    def advise(self, frame: np.ndarray, goal: str = "resource") -> Optional["Advice"]:
        """Ask Claude what to do. `goal` is 'resource' or 'deposit'. Returns None on failure."""
        if not self.cooled_down():
            return None
        self._last_call = time.time()

        question = (
            "Find the nearest harvestable tree or rock and tell me how to reach it."
            if goal == "resource"
            else "Find the deposit point / storehouse and tell me how to reach it."
        )
        b64 = self._encode(frame)

        try:
            resp = self.client.messages.parse(
                model=self.cfg.get("model", "claude-opus-4-8"),
                max_tokens=1024,
                thinking={"type": "adaptive"},
                output_config={"effort": self.cfg.get("effort", "low")},
                system=SYSTEM_PROMPT,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": b64,
                                },
                            },
                            {"type": "text", "text": question},
                        ],
                    }
                ],
                output_format=Advice,
            )
            return resp.parsed_output
        except Exception as exc:  # network/parse/refusal — never crash the loop
            print(f"[advisor] call failed: {exc}")
            return None
