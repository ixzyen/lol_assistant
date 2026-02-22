"""
LoL Kill Calculator Assistant — Main Entry Point

Hotkeys:
  F9   — toggle calculator on/off
  F10  — quit completely

When active, the calculator runs every POLL_INTERVAL seconds:
  1. Fetch my state from Live Client API
  2. Read enemy HP% from screen
  3. Run kill calculation for the enemy jungler (or most dangerous enemy)
  4. Display result on overlay
  5. Auto-pause when conditions not met (low HP, early game, late game, etc.)

Requirements (install before running):
  pip install requests keyboard mss opencv-python psutil
"""

import sys
import time
import logging
import threading
import psutil

# Allow running from project root
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import keyboard
except ImportError:
    print("ERROR: 'keyboard' not installed. Run: pip install keyboard")
    sys.exit(1)

from modules.live_client    import (is_game_active, get_my_state,
                                    get_enemies_state, get_my_team,
                                    get_game_time)
from modules.screen_reader  import read_enemy_hp_percents
from modules.target_panel_reader import read_target_panel, calibrate_target_panel
from modules.kill_calculator import calculate_kill_chance, format_result
from modules.overlay         import get_overlay

# ── Config ─────────────────────────────────────────────────────────────────────
POLL_INTERVAL   = 0.3    # seconds between calculations (~300ms refresh)
TARGET_POSITION = "JUNGLE"  # prioritize enemy jungler; fallback to all
HOTKEY_TOGGLE   = "ctrl+f1"   # show/hide overlay
HOTKEY_HIDE     = "ctrl+f2"   # hide only
HOTKEY_QUIT     = "ctrl+f3"   # full quit
CPU_THROTTLE_PCT = 75    # pause extra if CPU > this %

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("main")


# ── State ──────────────────────────────────────────────────────────────────────
class AppState:
    def __init__(self):
        self.active      = False
        self.running     = True
        self._lock       = threading.Lock()

    def toggle(self):
        with self._lock:
            self.active = not self.active
        status = "ON" if self.active else "OFF"
        print(f"[{time.strftime('%H:%M:%S')}] Calculator {status}")

    def quit(self):
        with self._lock:
            self.running = False
            self.active  = False
        print("Quitting...")


app = AppState()
_last_known_hp: dict = {}  # champion -> hp_percent, persists between ticks


# ── Target selection ───────────────────────────────────────────────────────────

# Locked target index (0-4), None = auto (lowest HP)
_locked_target_idx: int | None = None

def set_locked_target(idx: int | None):
    global _locked_target_idx
    _locked_target_idx = idx
    if idx is None:
        print("[Target] Auto mode (lowest HP)")
    else:
        print(f"[Target] Locked to slot {idx + 1}")

def pick_target(enemies: list[dict], preferred_name: str | None = None) -> dict | None:
    alive = [e for e in enemies if not e.get("is_dead", False)]
    if not alive:
        return None

    # Use locked index if set
    if _locked_target_idx is not None and _locked_target_idx < len(enemies):
        t = enemies[_locked_target_idx]
        if not t.get("is_dead", False):
            return t

    # Auto: lowest HP
    return min(alive, key=lambda e: e.get("hp_percent") or 1.0)


# ── Main loop ──────────────────────────────────────────────────────────────────

def main_loop():
    overlay = get_overlay()
    print(f"[{time.strftime('%H:%M:%S')}] LoL Kill Calculator ready.")
    print(f"  {HOTKEY_TOGGLE.upper()} — toggle on/off")
    print(f"  {HOTKEY_QUIT.upper()}  — quit")

    while app.running:
        time.sleep(POLL_INTERVAL)

        if not app.active:
            overlay.hide()
            continue

        print(f"[DEBUG] Loop tick - game_active check...")

        # CPU throttle
        cpu = psutil.cpu_percent(interval=None)
        if cpu > CPU_THROTTLE_PCT:
            logger.debug(f"CPU {cpu}% — throttling")
            time.sleep(0.5)
            continue

        # Check game is running
        if not is_game_active():
            print("[DEBUG] Game not active")
            overlay.update("[ WAITING ] No active game detected...", "PAUSED")
            overlay.show()
            continue
        print("[DEBUG] Game active, fetching state...")

        # Fetch data
        my_state  = get_my_state()
        game_time = get_game_time()

        if not my_state:
            overlay.update("[ ERROR ] Cannot reach Live Client API", "PAUSED")
            overlay.show()
            continue

        my_team   = get_my_team()
        enemies   = get_enemies_state(my_team)

        print(f"[DEBUG] champion={my_state.get('champion')} enemies={len(enemies)} team={my_team} hp={my_state.get('hp_percent'):.2f} game_time={game_time:.0f}")

        if not enemies:
            overlay.update("[ WAITING ] No enemy data yet...", "PAUSED")
            overlay.show()
            continue

        # Read target panel (top-left, after clicking enemy)
        sct = getattr(get_overlay(), '_sct', None)
        try:
            import mss as _mss
            if not hasattr(main_loop, '_sct'):
                main_loop._sct = _mss.mss()
            panel = read_target_panel(main_loop._sct)
        except Exception:
            panel = {}

        target = pick_target(enemies)

        # If panel active, inject real-time HP into target and cache it
        champ_key = target.get("champion", "") if target else ""
        if panel.get("panel_active") and target:
            if panel.get("hp_percent") is not None:
                target["hp_percent"]  = panel["hp_percent"]
                _last_known_hp[champ_key] = panel["hp_percent"]  # cache
            if panel.get("hp_current") is not None:
                target["hp_current"]  = panel["hp_current"]
            if panel.get("hp_max") is not None:
                target["hp_max_real"] = panel["hp_max"]
        elif champ_key in _last_known_hp and target:
            # Panel not detected this tick — use last known HP instead of 100%
            target["hp_percent"] = _last_known_hp[champ_key]

        # Build enemy slot line for overlay header
        lock_idx = _locked_target_idx
        slot_line = "  ".join(
            f"[{'*' if i == lock_idx else i+1}]{e.get('champion','?')[:6]}"
            for i, e in enumerate(enemies)
        )

        if target is None:
            overlay.update("[ WAITING ] All enemies dead / no target", "PAUSED")
            overlay.show()
            continue

        # Run calculator
        final_hp = target.get("hp_percent")  # real-time if panel active, else estimated

        try:
            result = calculate_kill_chance(
                my_state          = my_state,
                enemy             = target,
                enemy_hp_percent  = final_hp,
                my_hp_percent     = my_state.get("hp_percent"),
                allies_nearby     = 0,
                game_time         = game_time,
            )
        except Exception as calc_err:
            logger.warning(f"Calculator error: {calc_err}")
            overlay.update("[ ERROR ] Calculation failed — retrying...", "PAUSED")
            overlay.show()
            continue

        # Format and display
        text = f"{slot_line}\n{format_result(result)}"
        verdict = "PAUSED" if result.paused else result.verdict
        panel_str = f"HP={panel.get('hp_current')}/{panel.get('hp_max')}" if panel.get('panel_active') else "panel=off"
        print(f"[DEBUG] Verdict: {verdict} | Target: {target.get('champion')} | {panel_str} | conf={result.confidence:.0%} | myHP={my_state.get('hp_percent'):.0%}")
        overlay.update(text, verdict)
        overlay.show()

        # Console log for debugging
        logger.debug(
            f"[{target['champion']}] verdict={result.verdict} "
            f"conf={result.confidence:.0%} dmg={result.real_damage:.0f} "
            f"effHP={result.enemy_effective_hp:.0f}"
        )


# ── Entry ──────────────────────────────────────────────────────────────────────

def main():
    # Register hotkeys
    keyboard.add_hotkey(HOTKEY_TOGGLE, app.toggle)
    keyboard.add_hotkey(HOTKEY_HIDE,   get_overlay().hide)
    keyboard.add_hotkey(HOTKEY_QUIT,   app.quit)
    # Ctrl+1..5 to lock target, Ctrl+0 to unlock
    for i in range(5):
        keyboard.add_hotkey(f"ctrl+{i+1}", lambda idx=i: set_locked_target(idx))
    keyboard.add_hotkey("ctrl+0", lambda: set_locked_target(None))

    # Run main loop in thread so keyboard hooks stay on main thread
    loop_thread = threading.Thread(target=main_loop, daemon=True)
    loop_thread.start()

    print(f"Hotkeys: {HOTKEY_TOGGLE.upper()} toggle | {HOTKEY_HIDE.upper()} hide | {HOTKEY_QUIT.upper()} quit")

    # Keep main thread alive for keyboard hooks
    while app.running:
        time.sleep(0.1)

    print("Goodbye.")
    sys.exit(0)


if __name__ == "__main__":
    main()
