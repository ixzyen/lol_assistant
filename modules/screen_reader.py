"""
Screen reader module.
Reads enemy HP% from the top scoreboard panel (always visible, no camera needed).

The top panel has 10 champion portraits in a row:
  - Left 5:  your team  (blue side = ORDER)
  - Right 5: enemy team (red side = CHAOS)

Each portrait has a thin HP bar below/above it.
We read the WIDTH ratio of that bar to determine HP%.
"""

import numpy as np
import logging
from typing import Optional
import time

logger = logging.getLogger(__name__)

# Try importing screen capture / CV libs gracefully
try:
    import mss
    import cv2
    LIBS_AVAILABLE = True
except ImportError:
    LIBS_AVAILABLE = False
    logger.warning("mss or cv2 not installed. Screen reading disabled.")


# ── Region configuration ───────────────────────────────────────────────────────
# Calibrated for 2560x1440 with Blitz.gg overlay.
# Blitz moves champion portraits to bottom-right corner.
# HP bars appear below each portrait icon in that cluster.
#
# If you DON'T use Blitz, set USE_BLITZ_LAYOUT = False
# to use the standard top-panel layout instead.

USE_BLITZ_LAYOUT = True

BASE_WIDTH  = 2560
BASE_HEIGHT = 1440

# Standard LoL top panel (no Blitz) — 1440p coords
_ENEMY_HP_BARS_STANDARD_1440P = [
    (1350, 18, 88, 8),   # enemy 1
    (1458, 18, 88, 8),   # enemy 2
    (1566, 18, 88, 8),   # enemy 3
    (1674, 18, 88, 8),   # enemy 4
    (1782, 18, 88, 8),   # enemy 5
]

# Blitz.gg layout — calibrated for your 2560x1440 setup
_ENEMY_HP_BARS_BLITZ_1440P = [
    (1075, 496, 69, 9),  # enemy 1
    (1153, 496, 69, 9),  # enemy 2
    (1231, 496, 69, 9),  # enemy 3
    (1309, 496, 69, 9),  # enemy 4
    (1387, 496, 69, 9),  # enemy 5
]

_ENEMY_HP_BARS_1080P = (
    _ENEMY_HP_BARS_BLITZ_1440P if USE_BLITZ_LAYOUT
    else _ENEMY_HP_BARS_STANDARD_1440P
)

# HP bar color ranges in HSV
HP_COLOR_GREEN  = ([40,  100, 100], [80,  255, 255])
HP_COLOR_YELLOW = ([20,  100, 100], [39,  255, 255])
HP_COLOR_RED    = ([0,   150, 100], [10,  255, 255])
HP_COLOR_RED2   = ([170, 150, 100], [180, 255, 255])  # red wraps in HSV


def _scale_region(region: tuple, screen_w: int, screen_h: int) -> tuple:
    """Scale regions to actual screen resolution."""
    sx = screen_w / BASE_WIDTH
    sy = screen_h / BASE_HEIGHT
    x, y, w, h = region
    return (int(x * sx), int(y * sy), max(1, int(w * sx)), max(1, int(h * sy)))


def _detect_hp_ratio(bar_image: np.ndarray) -> float:
    """
    Given a cropped HP bar image, return HP ratio 0.0–1.0.
    Strategy: find the rightmost pixel that is green/yellow/red (HP color).
    The ratio = rightmost_hp_pixel / bar_total_width.
    """
    if bar_image is None or bar_image.size == 0:
        return 1.0  # assume full HP if can't read

    hsv = cv2.cvtColor(bar_image, cv2.COLOR_BGR2HSV)
    bar_w = bar_image.shape[1]

    # Combine masks for all HP colors
    mask_green  = cv2.inRange(hsv,
        np.array(HP_COLOR_GREEN[0]),  np.array(HP_COLOR_GREEN[1]))
    mask_yellow = cv2.inRange(hsv,
        np.array(HP_COLOR_YELLOW[0]), np.array(HP_COLOR_YELLOW[1]))
    mask_red1   = cv2.inRange(hsv,
        np.array(HP_COLOR_RED[0]),    np.array(HP_COLOR_RED[1]))
    mask_red2   = cv2.inRange(hsv,
        np.array(HP_COLOR_RED2[0]),   np.array(HP_COLOR_RED2[1]))

    combined = cv2.bitwise_or(mask_green, mask_yellow)
    combined = cv2.bitwise_or(combined, mask_red1)
    combined = cv2.bitwise_or(combined, mask_red2)

    # Collapse rows → 1D column presence
    col_presence = np.any(combined > 0, axis=0)
    hp_cols = np.where(col_presence)[0]

    if len(hp_cols) == 0:
        return 0.0  # bar appears empty

    rightmost = int(hp_cols.max())
    ratio = (rightmost + 1) / bar_w
    return min(1.0, max(0.0, ratio))


class ScreenReader:
    def __init__(self):
        self.available = LIBS_AVAILABLE
        self._sct = None
        self._screen_w = BASE_WIDTH
        self._screen_h = BASE_HEIGHT
        self._scaled_bars = _ENEMY_HP_BARS_1080P.copy()

        if self.available:
            self._sct = mss.mss()
            self._detect_resolution()

    def _detect_resolution(self):
        if not self.available:
            return
        monitor = self._sct.monitors[1]  # primary monitor
        self._screen_w = monitor["width"]
        self._screen_h = monitor["height"]
        self._scaled_bars = [
            _scale_region(r, self._screen_w, self._screen_h)
            for r in _ENEMY_HP_BARS_1080P
        ]
        logger.info(f"Screen resolution: {self._screen_w}x{self._screen_h}")

    def read_enemy_hp_percents(self) -> list[float]:
        """
        Returns list of 5 HP% values for enemy team (top panel, left to right).
        Values: 0.0 = dead, 1.0 = full HP.
        Falls back to [1.0] * 5 if screen reading fails.
        """
        if not self.available:
            return [1.0] * 5

        try:
            if USE_BLITZ_LAYOUT:
                cap_left, cap_top = 1050, 487
                cap_w = self._screen_w - 1050
                cap_h = 30
            else:
                cap_left, cap_top = 0, 0
                cap_w = self._screen_w
                cap_h = 60

            region = {"top": cap_top, "left": cap_left,
                      "width": cap_w, "height": cap_h}
            screenshot = self._sct.grab(region)
            frame = np.array(screenshot)
            frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

            hp_values = []
            for (x, y, w, h) in self._scaled_bars:
                rx = x - cap_left
                ry = y - cap_top
                y1, y2 = max(0, ry), min(frame.shape[0], ry + h)
                x1, x2 = max(0, rx), min(frame.shape[1], rx + w)
                bar_crop = frame[y1:y2, x1:x2]
                ratio = _detect_hp_ratio(bar_crop)
                hp_values.append(ratio)

            return hp_values

        except Exception as e:
            logger.warning(f"Screen read failed: {e}")
            return [1.0] * 5

    def calibrate_interactive(self):
        """
        Simple calibration helper.
        Captures a screenshot and saves it so you can measure bar coords manually.
        """
        if not self.available:
            print("Screen reading libs not available.")
            return

        fname = "calibration_screenshot.png"
        screenshot = self._sct.grab(self._sct.monitors[1])
        frame = np.array(screenshot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # Draw current bar regions
        for i, (x, y, w, h) in enumerate(self._scaled_bars):
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
            cv2.putText(frame, f"E{i+1}", (x, y - 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 255, 0), 1)

        cv2.imwrite(fname, frame)
        print(f"Saved calibration screenshot to {fname}")
        print("Check if green rectangles align with enemy HP bars in top panel.")
        print("If not, adjust _ENEMY_HP_BARS_1080P in screen_reader.py")


# Singleton
_reader: Optional[ScreenReader] = None

def get_reader() -> ScreenReader:
    global _reader
    if _reader is None:
        _reader = ScreenReader()
    return _reader


def read_enemy_hp_percents() -> list[float]:
    """Module-level convenience function."""
    return get_reader().read_enemy_hp_percents()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    reader = ScreenReader()
    print("Reading HP bars... (make sure LoL is in foreground)")
    time.sleep(1)
    values = reader.read_enemy_hp_percents()
    print(f"Enemy HP%: {[f'{v:.0%}' for v in values]}")
    reader.calibrate_interactive()


# ── Top-left target panel reader ──────────────────────────────────────────────
# When you click on an enemy champion, LoL shows their HP bar in the top-left.
# Region approximate for 2560x1440:
#   HP bar starts around x=95, y=22, width=195, height=11

_TARGET_HP_BAR_1440P = (95, 22, 195, 11)


def read_clicked_target_hp() -> float:
    """
    Read HP% of the currently clicked target from top-left panel.
    Returns 0.0-1.0, or None if panel not detected.
    """
    reader = get_reader()
    if not reader.available:
        return None

    try:
        sct = reader._sct
        region = {"top": 15, "left": 85, "width": 215, "height": 20}
        shot = sct.grab(region)
        frame = np.array(shot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        ratio = _detect_hp_ratio(frame)
        # Sanity check — if ratio is exactly 1.0 panel may not be visible
        if ratio > 0.98:
            return None  # likely no target selected
        return ratio
    except Exception as e:
        logger.warning(f"Target HP read failed: {e}")
        return None


# ── OCR target name reader ────────────────────────────────────────────────────
# When you click on a champion, LoL shows their name in top-left panel.
# Region for 2560x1440: name label is roughly x=90, y=5, w=200, h=18

_OCR_AVAILABLE = False
try:
    import pytesseract
    from PIL import Image
    _OCR_AVAILABLE = True
except ImportError:
    pass


def read_clicked_target_name() -> str | None:
    """
    Read the champion name from the top-left click panel using OCR.
    Returns champion name string (e.g. "Sona") or None if not detected.
    Requires: pip install pytesseract pillow  +  Tesseract installed on system.
    """
    if not _OCR_AVAILABLE:
        return None
    reader = get_reader()
    if not reader.available:
        return None

    try:
        pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"
        sct = reader._sct
        # Capture top-left panel name area — above the HP bar
        region = {"top": 2, "left": 85, "width": 220, "height": 20}
        shot = sct.grab(region)
        frame = np.array(shot)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

        # Upscale for better OCR accuracy
        frame = cv2.resize(frame, (frame.shape[1] * 3, frame.shape[0] * 3),
                           interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale and threshold (white text on dark bg)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 140, 255, cv2.THRESH_BINARY)

        img = Image.fromarray(thresh)
        raw = pytesseract.image_to_string(
            img,
            config="--psm 7 --oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz' "
        ).strip()

        # Clean up — take first word-like token, min 3 chars
        import re
        tokens = re.findall(r"[A-Za-z']{3,}", raw)
        if not tokens:
            return None

        name = " ".join(tokens[:2])  # e.g. "Lee Sin" = two tokens
        return name if len(name) >= 3 else None

    except Exception as e:
        logger.warning(f"OCR failed: {e}")
        return None
