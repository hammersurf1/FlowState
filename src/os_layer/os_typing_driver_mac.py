"""
OS-Level Keystroke Driver — macOS.

Types real keystrokes via pyautogui or keyboard library.
OS mode does NOT apply special formatting (BETA scope).
"""

import time

import pyperclip


class OsTypingDriverMac:
    """Types into whatever application has focus via OS-level keystrokes (macOS)."""

    def __init__(self):
        self._blocker_active = False

    def start_blocker(self):
        self._blocker_active = True
        # macOS doesn't have a simple 'block_key' like Windows.
        # We rely on the fact that the user isn't typing during paste.

    def stop_blocker(self):
        self._blocker_active = False

    def send_formatting_key(self, key):
        pass  # no-op

    def inject_html(self, html):
        pass  # no-op

    def is_google_docs(self):
        return False

    def detect_layout(self):
        return "QWERTY"

    def get_clipboard(self):
        return pyperclip.paste()

    def surgical_paste(self, content):
        pyperclip.copy(content)
        time.sleep(0.05)
        # Use Cmd+V on macOS
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
            timeout=5,
        )

    def send_char(self, char, dwell_time_seconds):
        import subprocess
        subprocess.run(
            ["osascript", "-e", f'tell application "System Events" to keystroke "{char}"'],
            timeout=2,
        )

    def send_backspace(self):
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to key code 51'],
            timeout=2,
        )

    def send_shift_enter(self):
        import subprocess
        subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to keystroke return using shift down'],
            timeout=2,
        )

    def send_enter(self):
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke return'],
            timeout=2,
        )

    def send_tab(self):
        import subprocess
        subprocess.run(
            ["osascript", "-e", 'tell application "System Events" to keystroke tab'],
            timeout=2,
        )

    def send_key(self, shortcut):
        # In OS mode, only pass through structural keys (Enter, Tab).
        # Formatting shortcuts are silently ignored.
        s = shortcut.lower()
        if "enter" in s or s == "tab":
            import subprocess
            key_name = "return" if "enter" in s else "tab"
            script = f'tell application "System Events" to keystroke {key_name}'
            subprocess.run(["osascript", "-e", script], timeout=2)
        # else: formatting shortcut — silently ignored
