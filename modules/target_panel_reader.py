"""
Target panel reader — reads enemy HP/mana from top-left click panel.

Only processes panel when HP bar is RED (enemy). Green bar = ally, ignored.
Coordinates calibrated for 2560x1440.
"""

import logging
import re
import numpy as np
import cv2

logger = logging.getLogger(__name__)

# ── Coordinates (measured by user, 2560x1440) ─────────────────────────────────
# HP: current starts x=214,y=38  |  max starts x=247,y=39
# MP: current starts x=213,y=56  |  max starts x=244,y=56
#
# Capture regions: (left, top, width, height)
_HP_REGION    = (205, 32, 160, 16)   # "500 / 850"
_MP_REGION    = (205, 50, 160, 16)   # "300 / 450"

# HP bar color sample region — check if bar is RED (enemy) or GREEN (ally)
# Sample a small area in the middle of the HP bar fill
_HP_BAR_SAMPLE = (90, 36, 25, 10)   # left edge of HP bar — red even at very low HP

# HSV ranges for enemy HP bar (red/dark-red gradient)
# LoL HP bar is gradient: dark-red (left) → bright-red (right)
# Lower V threshold to 30 to catch dark left portion
_RED_LOW1  = np.array([  0, 60, 30])
_RED_HIGH1 = np.array([ 15, 255, 255])
_RED_LOW2  = np.array([160, 60, 30])
_RED_HIGH2 = np.array([180, 255, 255])

# HSV range for ally HP bar (green)
_GREEN_LOW  = np.array([ 35, 50, 30])
_GREEN_HIGH = np.array([100, 255, 255])

# Max plausible HP/mana values for sanity checking
_MAX_PLAUSIBLE_HP   = 8000
_MAX_PLAUSIBLE_MANA = 3000

# ── OCR setup ─────────────────────────────────────────────────────────────────
_OCR_READY = False
try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"
    _OCR_READY = True
except ImportError:
    logger.warning("pytesseract/PIL not installed — target panel reading disabled")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _grab(sct, left, top, width, height) -> np.ndarray:
    shot = sct.grab({"left": left, "top": top, "width": width, "height": height})
    frame = np.array(shot)
    return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)


def _is_enemy_panel(sct) -> bool:
    """
    Color detection disabled — too unreliable with LoL's gradient dark-red bar.
    Always returns True and lets OCR sanity checks filter bad reads.
    Don't click on ally champions to avoid false reads.
    """
    return True


def _preprocess_for_ocr(frame: np.ndarray):
    """Upscale + threshold light text on dark background."""
    big = cv2.resize(frame, (frame.shape[1] * 4, frame.shape[0] * 4),
                     interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(big, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY)
    return Image.fromarray(thresh)


def _ocr_pair(img, max_plausible: int) -> tuple | None:
    """
    Parse 'current / max' from OCR image.
    Returns (current, max) ints or None.
    """
    raw = pytesseract.image_to_string(
        img,
        config="--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/ "
    ).strip()

    nums = re.findall(r'\d+', raw)
    if len(nums) < 2:
        return None

    cur, mx = int(nums[0]), int(nums[1])

    # Sanity: plausible range
    if mx == 0 or mx > max_plausible:
        return None
    # Sanity: current can't be wildly more than max (OCR misread)
    if cur > mx * 1.1:
        return None
    # Sanity: clamp regen overshoot
    if cur > mx:
        cur = mx
    if cur < 0:
        return None
    # Sanity: minimum plausible HP (avoid reading UI noise as "5/8" etc.)
    if mx < 100:
        return None

    return cur, mx


# ── Public API ────────────────────────────────────────────────────────────────

def read_target_panel(sct) -> dict:
    """
    Read HP and mana from top-left target panel.
    Only processes if HP bar is RED (enemy). Returns panel_active=False otherwise.

    Returns dict:
      panel_active  — bool
      hp_current    — int or None
      hp_max        — int or None
      hp_percent    — float 0-1 or None
      mp_current    — int or None
      mp_max        — int or None
      mp_percent    — float 0-1 or None

    # ── Future extension ──────────────────────────────────────────────────────
    # Stats below are NOT available via Riot Live Client API for enemies.
    # To add: measure coordinates of each stat value in the panel,
    # add a capture region + OCR call per stat, same pattern as HP/mana.
    #   ad      — enemy current AD
    #   ap      — enemy current AP
    #   armor   — enemy current armor  
    #   mr      — enemy current MR
    #   lethality, pen etc.
    # ─────────────────────────────────────────────────────────────────────────
    """
    result = {
        "panel_active": False,
        "hp_current":   None,
        "hp_max":       None,
        "hp_percent":   None,
        "mp_current":   None,
        "mp_max":       None,
        "mp_percent":   None,
    }

    if not _OCR_READY:
        return result

    try:
        # Only process enemy panels (red HP bar)
        if not _is_enemy_panel(sct):
            return result

        # ── HP ──
        hp_frame = _grab(sct, *_HP_REGION)
        hp_pair  = _ocr_pair(_preprocess_for_ocr(hp_frame), _MAX_PLAUSIBLE_HP)
        if hp_pair:
            cur, mx = hp_pair
            result["hp_current"]  = cur
            result["hp_max"]      = mx
            result["hp_percent"]  = cur / mx
            result["panel_active"] = True

        # ── Mana ──
        mp_frame = _grab(sct, *_MP_REGION)
        mp_pair  = _ocr_pair(_preprocess_for_ocr(mp_frame), _MAX_PLAUSIBLE_MANA)
        if mp_pair:
            cur, mx = mp_pair
            result["mp_current"] = cur
            result["mp_max"]     = mx
            result["mp_percent"] = cur / mx

    except Exception as e:
        logger.debug(f"Target panel read: {e}")

    return result


def calibrate_target_panel(sct):
    """Debug tool — run in-game with enemy clicked. Saves PNG + prints OCR output."""
    hp_frame = _grab(sct, *_HP_REGION)
    mp_frame = _grab(sct, *_MP_REGION)
    bar_sample = _grab(sct, *_HP_BAR_SAMPLE)

    hp_big  = cv2.resize(hp_frame,    (hp_frame.shape[1]*4,    hp_frame.shape[0]*4))
    mp_big  = cv2.resize(mp_frame,    (mp_frame.shape[1]*4,    mp_frame.shape[0]*4))
    bar_big = cv2.resize(bar_sample,  (bar_sample.shape[1]*4,  bar_sample.shape[0]*4))

    # Resize all strips to same width before stacking
    w = hp_big.shape[1]
    mp_big  = cv2.resize(mp_big,  (w, mp_big.shape[0]))
    bar_big = cv2.resize(bar_big, (w, bar_big.shape[0]))
    sep = np.zeros((4, w, 3), dtype=np.uint8)
    combined = np.vstack([hp_big, sep, mp_big, sep, bar_big])
    cv2.imwrite("target_panel_calibration.png", combined)

    enemy = _is_enemy_panel(sct)
    print(f"Panel detected as: {'ENEMY (red)' if enemy else 'ALLY (green) or NONE'}")

    # Debug: show actual HSV values in the sample region
    sample = _grab(sct, *_HP_BAR_SAMPLE)
    hsv = cv2.cvtColor(sample, cv2.COLOR_BGR2HSV)
    avg_hsv = hsv.mean(axis=(0,1))
    print(f"HP bar sample avg HSV: H={avg_hsv[0]:.1f} S={avg_hsv[1]:.1f} V={avg_hsv[2]:.1f}")
    red1  = cv2.inRange(hsv, _RED_LOW1,  _RED_HIGH1)
    red2  = cv2.inRange(hsv, _RED_LOW2,  _RED_HIGH2)
    green = cv2.inRange(hsv, _GREEN_LOW, _GREEN_HIGH)
    print(f"Red pixels: {cv2.countNonZero(cv2.bitwise_or(red1,red2))} / {sample.shape[0]*sample.shape[1]} total")
    print(f"Green pixels: {cv2.countNonZero(green)} / {sample.shape[0]*sample.shape[1]} total")

    if _OCR_READY:
        hp_raw = pytesseract.image_to_string(
            _preprocess_for_ocr(hp_frame),
            config="--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/ "
        ).strip()
        mp_raw = pytesseract.image_to_string(
            _preprocess_for_ocr(mp_frame),
            config="--psm 7 --oem 3 -c tessedit_char_whitelist=0123456789/ "
        ).strip()
        print(f"HP OCR raw : {repr(hp_raw)}")
        print(f"MP OCR raw : {repr(mp_raw)}")
        print(f"HP parsed  : {_ocr_pair(_preprocess_for_ocr(hp_frame), _MAX_PLAUSIBLE_HP)}")
        print(f"MP parsed  : {_ocr_pair(_preprocess_for_ocr(mp_frame), _MAX_PLAUSIBLE_MANA)}")

    print("Saved target_panel_calibration.png (top=HP, mid=MP, bottom=bar color sample)")
