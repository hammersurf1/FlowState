"""
FlowState — Hybrid Typing Driver (Windows)

Routes typing to the Playwright CDP path when:
  - The foreground window is the FlowState Chrome instance (detected by
    the 'FlowStateChromeProfile' marker in its command line), AND
  - Port 9225 is actually accepting connections.

Otherwise falls back to OS-level keystrokes so typing works in ANY application.

Implements the exact same interface as PlaywrightDriverWin — the engine
requires zero changes.
"""

import ctypes
import socket
import subprocess
import time


from .os_typing_driver_win import OsTypingDriverWin
from .playwright_driver_win import PlaywrightDriverWin


class HybridDriver:
    """
    Auto-detects whether typing should go through Playwright (CDP) or
    OS-level keystrokes based on foreground window and CDP availability.

    Never auto-launches anything.  If CDP is unreachable, falls back to
    OS mode silently.
    """

    FLOWSTATE_PROFILE_MARKER = "FlowStateChromeProfile"

    def __init__(self, playwright_instance):
        self.p = playwright_instance
        self.pw_driver = PlaywrightDriverWin(playwright_instance)
        self.os_driver = OsTypingDriverWin()
        self._mode = None  # 'playwright' | 'os' | None

    # ── Foreground-window detection ───────────────────────────────

    @staticmethod
    def _get_foreground_pid():
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        pid = ctypes.c_ulong(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    @staticmethod
    def _get_cmdline_for_pid(pid):
        """Read the command line of a process by PID via PowerShell."""
        try:
            result = subprocess.run(
                [
                    "powershell",
                    "-Command",
                    f"Get-CimInstance Win32_Process -Filter 'ProcessId = {pid}' | "
                    f"Select-Object -ExpandProperty CommandLine",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            return result.stdout.strip()
        except Exception:
            return ""

    @staticmethod
    def _is_cdp_reachable():
        """Quick TCP probe — is localhost:9225 accepting connections?"""
        try:
            sock = socket.create_connection(("localhost", 9225), timeout=0.5)
            sock.close()
            return True
        except Exception:
            return False

    def _is_flowstate_chrome_foreground(self):
        """True if the foreground window appears to be Chrome with remote debugging."""
        pid = self._get_foreground_pid()
        if not pid:
            return False
        cmdline = self._get_cmdline_for_pid(pid)
        # Accept any Chrome with --remote-debugging-port, not just our shortcut
        return ("chrome" in cmdline.lower() and
                ("remote-debugging-port" in cmdline or
                 self.FLOWSTATE_PROFILE_MARKER in cmdline))

    # ── Lifecycle ─────────────────────────────────────────────────

    def attach(self, window_title=None):
        """Choose mode and attach the appropriate driver."""
        if self._mode is not None:
            # Already attached for this paste session — reuse.
            if self._mode == "playwright":
                try:
                    self.pw_driver.attach(window_title)
                except Exception as e:
                    print(f"Playwright attach failed mid-session: {e}")
                    self._mode = "os"
                    self.os_driver.start_blocker()
            else:
                self.os_driver.start_blocker()
            return

        # Decide mode: must have BOTH the FlowState Chrome in foreground
        # AND port 9225 accepting connections.
        if self._is_flowstate_chrome_foreground() and self._is_cdp_reachable():
            try:
                self.pw_driver.attach(window_title)
                self._mode = "playwright"
                return
            except Exception as e:
                print(f"Playwright attach failed ({e}). Falling back to OS mode.")
                # Fall through to OS mode

        # Default: OS mode
        self._mode = "os"
        self.os_driver.start_blocker()

    def detach(self):
        """Detach the active driver."""
        if self._mode == "playwright":
            self.pw_driver.detach()
        elif self._mode == "os":
            self.os_driver.stop_blocker()
        self._mode = None

    # ── Google Docs detection ─────────────────────────────────────

    def is_playwright_mode(self):
        """True if the driver is currently in Playwright (CDP) mode."""
        return self._mode == "playwright"

    def is_google_docs(self):
        """True if active page is a Google Docs document (Playwright only)."""
        if self._mode == "playwright":
            return self.pw_driver.is_google_docs()
        return False

    # ── Formatting helpers (delegate to active driver) ────────────

    def send_formatting_key(self, key):
        if self._mode == "playwright":
            self.pw_driver.send_formatting_key(key)
        else:
            self.os_driver.send_formatting_key(key)  # no-op in OS mode

    def inject_html(self, html):
        if self._mode == "playwright":
            self.pw_driver.inject_html(html)
        else:
            self.os_driver.inject_html(html)  # no-op

    # ── Shared helpers ────────────────────────────────────────────

    def focus_page(self):
        if self._mode == "playwright":
            self.pw_driver.focus_page()

    def focus_editor(self):
        """Focus the Google Docs editing surface once at session start."""
        if self._mode == "playwright":
            self.pw_driver._focus_editor()

    def detect_layout(self):
        # Layout detection works the same regardless of mode.
        return self.os_driver.detect_layout()

    def get_clipboard(self):
        return self.os_driver.get_clipboard()

    # ── Typing actions (routed to the active sub-driver) ──────────

    def surgical_paste(self, content):
        if self._mode == "playwright":
            self.pw_driver.surgical_paste(content)
        else:
            self.os_driver.surgical_paste(content)

    def send_char(self, char, dwell_time_seconds):
        if self._mode == "playwright":
            self.pw_driver.send_char(char, dwell_time_seconds)
        else:
            self.os_driver.send_char(char, dwell_time_seconds)

    def send_backspace(self):
        if self._mode == "playwright":
            self.pw_driver.send_backspace()
        else:
            self.os_driver.send_backspace()

    def send_shift_enter(self):
        if self._mode == "playwright":
            self.pw_driver.send_shift_enter()
        else:
            self.os_driver.send_shift_enter()

    def send_enter(self):
        if self._mode == "playwright":
            self.pw_driver.send_enter()
        else:
            self.os_driver.send_enter()

    def send_tab(self):
        if self._mode == "playwright":
            self.pw_driver.send_tab()
        else:
            self.os_driver.send_tab()

    def send_key(self, shortcut):
        if self._mode == "playwright":
            self.pw_driver.send_key(shortcut)
        else:
            self.os_driver.send_key(shortcut)
