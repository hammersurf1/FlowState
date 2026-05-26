"""
OS-Level Keystroke Driver — Windows.

Types real keystrokes via the ``keyboard`` library. Works in ANY
application — Notepad, Word, Firefox, regular Chrome, etc.

OS mode does NOT apply formatting (BETA). Formatting shortcuts are
silently ignored; only structural keys (Enter, Tab) are passed through.
"""

import time
import keyboard
import pyperclip


class OsTypingDriverWin:
    """Types into whatever application has focus via OS-level keystrokes."""

    def __init__(self):
        self._hook = None
        self._typing_in_progress = False
        self._blocker_active = False
        self._debug = False  # set by engine if debug mode enabled

    # ── Lifecycle ────────────────────────────────────────────────

    def start_blocker(self):
        """Suppress user keystrokes during FlowState typing.

        Uses keyboard.hook with suppress=True and a flag so FlowState's
        own injected keystrokes are NOT suppressed.
        """
        if self._blocker_active:
            return
        self._typing_in_progress = False
        self._hook = keyboard.hook(self._hook_callback, suppress=True)
        self._blocker_active = True
        if self._debug:
            print("[FlowState DEBUG] OS blocker ON (hook active)")

    def stop_blocker(self):
        """Restore normal keyboard input."""
        if not self._blocker_active:
            return
        if self._hook:
            try:
                keyboard.unhook(self._hook)
            except Exception:
                pass
            self._hook = None
        self._typing_in_progress = False
        self._blocker_active = False
        if self._debug:
            print("[FlowState DEBUG] OS blocker OFF (hook removed)")

    def _hook_callback(self, event):
        """Allow FlowState's own keystrokes through, suppress user input."""
        if self._typing_in_progress:
            return True  # allow FlowState's injected keystrokes
        return False  # suppress all physical user keystrokes

    def _enter_typing(self):
        """Mark that FlowState is about to inject keystrokes."""
        self._typing_in_progress = True

    def _exit_typing(self):
        """Mark that FlowState finished injecting keystrokes."""
        self._typing_in_progress = False

    # ── Formatting helpers (no-ops in OS mode — beta) ────────────

    def send_formatting_key(self, key):
        pass  # OS mode doesn't do formatting

    def inject_html(self, html):
        pass  # OS mode can't inject HTML

    def is_google_docs(self):
        return False

    # ── Layout / clipboard ───────────────────────────────────────

    def detect_layout(self):
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
        self._enter_typing()
        try:
            pyperclip.copy(content)
            time.sleep(0.05)
            keyboard.send("ctrl+v")
        finally:
            self._exit_typing()

    def send_char(self, char, dwell_time_seconds):
        self._enter_typing()
        try:
            keyboard.write(char, delay=dwell_time_seconds)
        finally:
            self._exit_typing()

    def send_backspace(self):
        self._enter_typing()
        try:
            keyboard.send("backspace")
        finally:
            self._exit_typing()

    def send_shift_enter(self):
        self._enter_typing()
        try:
            keyboard.send("shift+enter")
        finally:
            self._exit_typing()

    def send_enter(self):
        self._enter_typing()
        try:
            keyboard.send("enter")
        finally:
            self._exit_typing()

    def send_tab(self):
        self._enter_typing()
        try:
            keyboard.send("tab")
        finally:
            self._exit_typing()

    def send_key(self, shortcut):
        """In OS mode, only pass through structural keys (Enter, Tab).

        Formatting shortcuts (Ctrl+B, Ctrl+I, etc.) are silently ignored
        because they trigger browser/OS functions instead of formatting.
        """
        s = shortcut.lower().replace("control", "ctrl").replace("meta", "win")
        parts = set(s.replace("+", " ").split())
        if "enter" in parts:
            self._enter_typing()
            try:
                keyboard.send(s)
            finally:
                self._exit_typing()
        elif s.strip() == "tab":
            self._enter_typing()
            try:
                keyboard.send("tab")
            finally:
                self._exit_typing()
        # else: formatting shortcut — silently ignored in OS mode
