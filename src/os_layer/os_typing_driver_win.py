"""
OS-Level Keystroke Driver — Windows.

Types real keystrokes via the ``keyboard`` library. Works in ANY
application — Notepad, Word, Firefox, regular Chrome, etc.

For OS mode, all formatting is BETA — OS mode currently does NOT apply
special formatting.  Text is typed literally.
"""

import time

import keyboard
import pyperclip


class OsTypingDriverWin:
    """Types into whatever application has focus via OS-level keystrokes."""

    def __init__(self):
        self._blocker_active = False
        self._blocked_keys = set()

    # ── Lifecycle ────────────────────────────────────────────────

    def start_blocker(self):
        """Suppress real keystrokes while FlowState is typing.

        This prevents the user's actual keys from being interleaved
        with the synthetic keystrokes we're sending.
        """
        if self._blocker_active:
            return
        # Block all common printable and modifier keys
        self._blocked_keys = set()
        for c in "abcdefghijklmnopqrstuvwxyz0123456789":
            keyboard.block_key(c)
            self._blocked_keys.add(c)
        keyboard.block_key("space")
        self._blocked_keys.add("space")
        for c in (
            "`", "-", "=", "[", "]", "\\", ";", "'", ",", ".", "/",
            "backspace", "enter", "tab", "shift", "ctrl", "alt",
            "up", "down", "left", "right", "delete", "home", "end",
            "page up", "page down", "caps lock",
        ):
            keyboard.block_key(c)
            self._blocked_keys.add(c)
        self._blocker_active = True

    def stop_blocker(self):
        """Restore normal keyboard input."""
        if not self._blocker_active:
            return
        for c in self._blocked_keys:
            try:
                keyboard.unblock_key(c)
            except Exception:
                pass
        self._blocked_keys.clear()
        self._blocker_active = False

    # ── Formatting helpers (no-ops in OS mode — beta) ────────────

    def send_formatting_key(self, key):
        """Stub — OS mode doesn't do special formatting (beta)."""
        pass

    def inject_html(self, html):
        """Stub — OS mode can't inject HTML."""
        pass

    def is_google_docs(self):
        """OS mode — unknown what's focused."""
        return False

    # ── Layout / clipboard ───────────────────────────────────────

    def detect_layout(self):
        """Return the active keyboard layout name."""
        try:
            from ctypes import windll
            user32 = windll.user32
            hwnd = user32.GetForegroundWindow()
            tid = user32.GetWindowThreadProcessId(hwnd, 0)
            lang_id = user32.GetKeyboardLayout(tid) & 0xFFFF
            if lang_id == 0x0407:
                return "QWERTZ"
            if lang_id == 0x040C:
                return "AZERTY"
        except Exception:
            pass
        return "QWERTY"

    def get_clipboard(self):
        return pyperclip.paste()

    def focus_page(self):
        pass  # OS mode — app already focused

    # ── Typing actions ───────────────────────────────────────────

    def surgical_paste(self, content):
        """Paste content via clipboard + Ctrl+V (literal, no formatting)."""
        pyperclip.copy(content)
        time.sleep(0.05)
        keyboard.send("ctrl+v")

    def send_char(self, char, dwell_time_seconds):
        """Type a single character using real keystrokes."""
        keyboard.write(char, delay=dwell_time_seconds)

    def send_backspace(self):
        keyboard.send("backspace")

    def send_shift_enter(self):
        keyboard.send("shift+enter")

    def send_enter(self):
        keyboard.send("enter")

    def send_tab(self):
        keyboard.send("tab")

    def send_key(self, shortcut):
        """Send an arbitrary shortcut like 'ctrl+b'."""
        keyboard.send(shortcut)
