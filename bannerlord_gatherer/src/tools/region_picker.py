"""Helper: capture a full screenshot and print pixel coords as you click.

Run this, then click the top-left and bottom-right corners of the UI element
you want to define (e.g. the capacity widget). It prints a ready-to-paste
{left, top, width, height} block for config.yaml.

    python -m src.tools.region_picker
"""
from __future__ import annotations

import mss
import numpy as np

try:
    import cv2
except ImportError:
    raise SystemExit("opencv-python is required: pip install opencv-python")


def main():
    with mss.mss() as sct:
        mon = sct.monitors[1]
        frame = np.asarray(sct.grab(mon))[:, :, :3]

    clicks = []

    def on_mouse(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            clicks.append((x, y))
            print(f"click {len(clicks)}: ({x}, {y})")
            if len(clicks) == 2:
                (x1, y1), (x2, y2) = clicks
                left, top = min(x1, x2), min(y1, y2)
                w, h = abs(x2 - x1), abs(y2 - y1)
                print("\nPaste into config.yaml:")
                print(f"region: {{ left: {left}, top: {top}, width: {w}, height: {h} }}")

    cv2.namedWindow("region picker (click 2 corners, q to quit)", cv2.WINDOW_NORMAL)
    cv2.setMouseCallback("region picker (click 2 corners, q to quit)", on_mouse)
    while True:
        cv2.imshow("region picker (click 2 corners, q to quit)", frame)
        if cv2.waitKey(20) & 0xFF == ord("q"):
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
