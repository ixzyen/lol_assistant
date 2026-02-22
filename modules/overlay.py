"""
Overlay module — transparent always-on-top window.
Renders kill calculator output on top of the game.

Uses tkinter (built-in Python) — no extra installs needed.
Window is click-through on Windows via ctypes.
"""

import tkinter as tk
import threading
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Color scheme ───────────────────────────────────────────────────────────────
BG_COLOR       = "#0a0a0a"
BG_ALPHA       = 0.82           # window transparency (0=invisible, 1=opaque)
TEXT_COLOR     = "#e0e0e0"
COLOR_GO       = "#00ff88"      # green
COLOR_RISKY    = "#ffcc00"      # yellow
COLOR_NOGO     = "#ff4444"      # red
COLOR_PAUSED   = "#888888"      # grey
COLOR_FLAG     = "#ff9944"      # orange for warnings
FONT_MAIN      = ("Consolas", 11, "bold")
FONT_SMALL     = ("Consolas", 10)
FONT_VERDICT   = ("Consolas", 16, "bold")

# Window position (top-right, adjust as needed)
WINDOW_X = 1380
WINDOW_Y = 60
WINDOW_W = 520


class KillOverlay:
    def __init__(self):
        self._root:   Optional[tk.Tk]   = None
        self._thread: Optional[threading.Thread] = None
        self._ready   = threading.Event()
        self._lock    = threading.Lock()
        self._pending_text: Optional[str] = None
        self._pending_verdict: str = "NO GO"
        self._visible = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def start(self):
        """Start overlay in background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run_tk, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3.0)

    def stop(self):
        """Hide overlay (don't destroy — reuse on next start)."""
        self._visible = False
        if self._root:
            try:
                self._root.after(0, self._root.withdraw)
            except Exception:
                pass

    def update(self, text: str, verdict: str = "NO GO"):
        """Thread-safe update of overlay content."""
        with self._lock:
            self._pending_text    = text
            self._pending_verdict = verdict
        if self._root:
            try:
                self._root.after(0, self._apply_update)
            except Exception:
                pass

    def show(self):
        if self._root:
            try:
                self._root.after(0, self._root.deiconify)
                self._visible = True
            except Exception:
                pass

    def hide(self):
        self.stop()

    # ── Internal tk thread ─────────────────────────────────────────────────────

    def _run_tk(self):
        try:
            self._root = tk.Tk()
            self._setup_window()
            self._setup_widgets()
            self._make_click_through()
            self._ready.set()
            self._root.mainloop()
        except Exception as e:
            logger.error(f"Overlay error: {e}")
            self._ready.set()

    def _setup_window(self):
        r = self._root
        r.title("LoL Kill Calc")
        r.configure(bg=BG_COLOR)
        r.attributes("-topmost", True)
        r.attributes("-alpha", BG_ALPHA)
        r.overrideredirect(True)          # no window border/title bar
        r.geometry(f"{WINDOW_W}x200+{WINDOW_X}+{WINDOW_Y}")
        r.withdraw()                      # start hidden
        r.update()                        # force initial render

    def _setup_widgets(self):
        r = self._root

        # Outer frame with colored border (verdict color)
        self._border_frame = tk.Frame(r, bg=COLOR_NOGO, padx=2, pady=2)
        self._border_frame.pack(fill=tk.BOTH, expand=True)

        inner = tk.Frame(self._border_frame, bg=BG_COLOR, padx=8, pady=6)
        inner.pack(fill=tk.BOTH, expand=True)

        # Verdict line (big)
        self._verdict_label = tk.Label(
            inner, text="", font=FONT_VERDICT,
            bg=BG_COLOR, fg=COLOR_NOGO, anchor="w")
        self._verdict_label.pack(fill=tk.X)

        # Separator
        tk.Frame(inner, height=1, bg="#333333").pack(fill=tk.X, pady=3)

        # Main text block
        self._text_label = tk.Label(
            inner, text="", font=FONT_SMALL,
            bg=BG_COLOR, fg=TEXT_COLOR,
            justify=tk.LEFT, anchor="nw")
        self._text_label.pack(fill=tk.BOTH, expand=True)

        # Footer
        tk.Frame(inner, height=1, bg="#333333").pack(fill=tk.X, pady=3)
        footer = tk.Label(
            inner,
            text="CTRL+F1 toggle | CTRL+0 auto | CTRL+1-5 lock target",
            font=("Consolas", 9), bg=BG_COLOR, fg="#555555")
        footer.pack(anchor="e")

    def _apply_update(self):
        with self._lock:
            text    = self._pending_text
            verdict = self._pending_verdict

        if text is None:
            return

        verdict_color = {
            "GO":     COLOR_GO,
            "RISKY":  COLOR_RISKY,
            "NO GO":  COLOR_NOGO,
            "PAUSED": COLOR_PAUSED,
        }.get(verdict, COLOR_PAUSED)

        # Extract first line as verdict line, rest as body
        lines = text.split("\n")
        first = lines[0] if lines else ""
        body  = "\n".join(lines[1:]) if len(lines) > 1 else ""

        self._border_frame.configure(bg=verdict_color)
        self._verdict_label.configure(text=first, fg=verdict_color)
        self._text_label.configure(text=body)

        # Resize window height to fit content
        self._root.update_idletasks()
        req_h = self._root.winfo_reqheight()
        self._root.geometry(f"{WINDOW_W}x{req_h}+{WINDOW_X}+{WINDOW_Y}")

    def _make_click_through(self):
        """Make window click-through on Windows so it doesn't block game input."""
        try:
            import ctypes
            self._root.update_idletasks()
            hwnd = ctypes.windll.user32.FindWindowW(None, "LoL Kill Calc")
            if hwnd:
                style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
                ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x80000 | 0x20)
                ctypes.windll.user32.SetLayeredWindowAttributes(hwnd, 0, int(255 * 0.85), 0x2)
        except Exception:
            pass


# Singleton overlay
_overlay: Optional[KillOverlay] = None

def get_overlay() -> KillOverlay:
    global _overlay
    if _overlay is None:
        _overlay = KillOverlay()
        _overlay.start()
    return _overlay
