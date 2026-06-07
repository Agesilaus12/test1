"""Fast screen capture using mss. Returns BGR numpy frames for OpenCV/OCR."""
from __future__ import annotations

import numpy as np
import mss


class ScreenCapture:
    def __init__(self, region: dict):
        # region: {left, top, width, height}
        self.monitor = {
            "left": int(region["left"]),
            "top": int(region["top"]),
            "width": int(region["width"]),
            "height": int(region["height"]),
        }
        self._sct = mss.mss()

    def grab(self) -> np.ndarray:
        """Capture the configured region as a BGR uint8 array (H, W, 3)."""
        shot = self._sct.grab(self.monitor)
        frame = np.asarray(shot)  # BGRA
        return frame[:, :, :3]    # drop alpha -> BGR

    def crop(self, frame: np.ndarray, region: dict) -> np.ndarray:
        """Crop a sub-region {left, top, width, height} out of a captured frame.

        The region is expressed in absolute screen coordinates (same space as
        the capture region), so we offset by the capture origin.
        """
        x = int(region["left"]) - self.monitor["left"]
        y = int(region["top"]) - self.monitor["top"]
        w, h = int(region["width"]), int(region["height"])
        return frame[y : y + h, x : x + w]

    def close(self) -> None:
        self._sct.close()
