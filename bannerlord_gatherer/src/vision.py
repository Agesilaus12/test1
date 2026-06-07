"""Local screen-reading: OCR the Alt-overlay text to locate targets and read capacity.

This is the fast, free perception layer that drives the real-time loop. EasyOCR
is used by default because it copes well with stylised game fonts over noisy
backgrounds. If it's too slow on your machine, switch to the pytesseract backend.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass
class Detection:
    text: str
    cx: float          # center x in frame pixels
    cy: float          # center y in frame pixels
    confidence: float


class OCRBackend:
    """Thin wrapper around EasyOCR with a graceful import."""

    def __init__(self, languages=("en",), gpu: bool = False):
        try:
            import easyocr  # imported lazily so the rest of the app runs without it
        except ImportError as exc:  # pragma: no cover
            raise ImportError(
                "easyocr is required for the local OCR backend. "
                "Install it with `pip install easyocr`, or swap in pytesseract."
            ) from exc
        self.reader = easyocr.Reader(list(languages), gpu=gpu)

    def read(self, image: np.ndarray) -> list[Detection]:
        """Return all text detections with their pixel centers."""
        results = self.reader.readtext(image)
        dets: list[Detection] = []
        for box, text, conf in results:
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            dets.append(
                Detection(
                    text=text.strip(),
                    cx=float(sum(xs) / len(xs)),
                    cy=float(sum(ys) / len(ys)),
                    confidence=float(conf),
                )
            )
        return dets


def preprocess_for_ocr(image: np.ndarray) -> np.ndarray:
    """Upscale + threshold a small UI crop to make OCR more reliable."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.resize(gray, None, fx=2.0, fy=2.0, interpolation=cv2.INTER_CUBIC)
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return thresh


def find_label(
    detections: list[Detection],
    keywords: list[str],
    min_conf: float = 0.3,
) -> Optional[Detection]:
    """Return the highest-confidence detection whose text contains any keyword."""
    kws = [k.lower() for k in keywords]
    best: Optional[Detection] = None
    for det in detections:
        if det.confidence < min_conf:
            continue
        low = det.text.lower()
        if any(kw in low for kw in kws):
            if best is None or det.confidence > best.confidence:
                best = det
    return best


def find_all_labels(
    detections: list[Detection],
    keywords: list[str],
    min_conf: float = 0.3,
) -> list[Detection]:
    kws = [k.lower() for k in keywords]
    out = []
    for det in detections:
        if det.confidence < min_conf:
            continue
        if any(kw in det.text.lower() for kw in kws):
            out.append(det)
    return out


def read_capacity(
    ocr: OCRBackend,
    capacity_crop: np.ndarray,
    pattern: str,
) -> Optional[tuple[int, int]]:
    """OCR the capacity widget and parse 'current / max'. Returns None if unreadable."""
    pre = preprocess_for_ocr(capacity_crop)
    dets = ocr.read(pre)
    blob = " ".join(d.text for d in dets)
    match = re.search(pattern, blob)
    if not match:
        return None
    current, maximum = int(match.group(1)), int(match.group(2))
    if maximum <= 0:
        return None
    return current, maximum
