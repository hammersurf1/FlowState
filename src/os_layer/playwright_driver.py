"""Chrome driver over CDP. This base class works on Linux; the Win/Mac
subclasses only override where Chrome lives, the profile dir and layout detection.

Navigate-away design: attach() pins ONE Page for the whole run and nothing ever
calls bring_to_front(), so the user can switch tabs/windows while typing. Keys are
dispatched over CDP straight to the pinned page, not to whatever has OS focus.
"""
import ctypes
import os
import shutil
import subprocess
import sys
import time

import pyperclip

# Chrome throttles/pauses hidden and occluded tabs; these keep the pinned tab live
# while the user works in another tab or window. They only apply to a Chrome that
# FlowState launches (or one the user launched with the same flags).
CHROME_FLAGS = [
    "--no-first-run",
    "--disable-renderer-backgrounding",
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-features=CalculateNativeWinOcclusion",
]

# 'plain' = textarea/input (no formatting possible), 'rich' = contenteditable
# (Canvas/TinyMCE, Gmail, ...). Only the frame that really has focus answers.
_FOCUS_JS = """() => {
  if (!document.hasFocus()) return null;
  const e = document.activeElement; if (!e) return null;
  if (e.tagName === 'TEXTAREA') return 'plain';
  if (e.tagName === 'INPUT' && !['button','checkbox','radio','submit','file'].includes(e.type)) return 'plain';
  return (e.isContentEditable || document.designMode === 'on') ? 'rich' : null;
}"""

_EXEC_JS = """([cmd, val]) => {
  if (!document.hasFocus()) return null;
  const e = document.activeElement;
  if (!(document.designMode === 'on' || (e && e.isContentEditable))) return null;
  return document.execCommand(cmd, false, val);
}"""


class PlaywrightDriver:
    def __init__(self, playwright_instance, port=None):
        self.p = playwright_instance
        self.port = int(port or os.environ.get("FLOWSTATE_CDP_PORT", 9225))
        self.browser = None
        self.context = None
        self.page = None

    # ─── Platform hooks (overridden by Win/Mac) ──────────────────────────────

    def chrome_candidates(self):
        return [shutil.which(n) for n in
                ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser")]

    def profile_dir(self):
        return os.path.expanduser("~/.flowstate/chrome-profile")

    def detect_layout(self):
        if sys.platform == "win32":
            try:
                user32 = ctypes.windll.user32
                thread_id = user32.GetWindowThreadProcessId(user32.GetForegroundWindow(), 0)
                lang_id = user32.GetKeyboardLayout(thread_id) & 0xFFFF
                if lang_id == 0x0407: return "QWERTZ"
                if lang_id == 0x040C: return "AZERTY"
            except Exception:
                pass
        return "QWERTY"

    # ─── Connection / tab pinning ────────────────────────────────────────────

    def _cdp_url(self):
        return f"http://localhost:{self.port}"

    def attach(self, window_title=None):
        if self.page and not self.page.is_closed():
            return  # already pinned (e.g. resume after pause): never re-select
        if not self.browser:
            self._connect()
        self.page = self._pick_page(window_title)

    def _connect(self):
        print(f"Attaching to Chrome on port {self.port}...")
        try:
            self.browser = self.p.chromium.connect_over_cdp(self._cdp_url())
            return
        except Exception:
            print("Not found. Attempting to auto-launch Chrome...")
        if not self._auto_launch_chrome():
            raise Exception("Could not find Google Chrome installed.")
        for _ in range(20):  # Chrome needs a moment to open the debugging port
            time.sleep(0.5)
            try:
                self.browser = self.p.chromium.connect_over_cdp(self._cdp_url())
                return
            except Exception:
                pass
        raise Exception(
            "Failed to open debugging port. If Chrome is already running, you MUST "
            f"completely close it or launch it with --remote-debugging-port={self.port} first!"
        )

    def detach(self):
        # Sever the connection completely when typing finishes
        print("Detaching from Chrome...")
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
        self.browser = self.context = self.page = None

    def _auto_launch_chrome(self):
        chrome = next((c for c in self.chrome_candidates() if c and os.path.exists(c)), None)
        if not chrome:
            return False
        profile = self.profile_dir()
        os.makedirs(profile, exist_ok=True)
        subprocess.Popen([chrome, f"--remote-debugging-port={self.port}",
                          f"--user-data-dir={profile}", *CHROME_FLAGS])
        return True

    @staticmethod
    def _safe_eval(page, script):
        for _ in range(3):
            try:
                return page.evaluate(script)
            except Exception:
                time.sleep(0.1)
        return False

    def _pick_page(self, window_title=None):
        pages = [p for c in self.browser.contexts for p in c.pages]
        if not pages:
            raise Exception("No browser tabs found! Playwright cannot type into a closed browser.")
        self.context = pages[0].context
        visible = lambda p: self._safe_eval(p, "document.visibilityState === 'visible'")

        # 1. Window title captured at hotkey time (most reliable). Chrome's title is
        #    "<Page Title> - Google Chrome". Skip empty titles ('' matches everything)
        #    and prefer the visible tab when several share a title.
        hint = (window_title or "").replace(" - Google Chrome", "").strip().lower()
        if hint:
            def title(p):
                try: return p.title().strip().lower()
                except Exception: return ""
            matches = [p for p in pages if title(p) and (title(p) in hint or hint in title(p))]
            if matches:
                return next((p for p in matches if visible(p)), matches[0])

        # 2. Page reporting focus, 3. visible page with a focused editor, 4. any visible
        for script in (
            "document.hasFocus()",
            "document.visibilityState === 'visible' && document.activeElement && "
            "(document.activeElement.tagName === 'TEXTAREA' || document.activeElement.tagName === 'INPUT' "
            "|| document.activeElement.isContentEditable)",
            "document.visibilityState === 'visible'",
        ):
            for p in pages:
                if self._safe_eval(p, script):
                    return p
        return pages[-1]  # 5. last resort: most recently opened tab

    # ─── Page introspection / rich-text helpers ──────────────────────────────

    def page_url(self):
        return self.page.url if self.page else ""

    def _first_frame_result(self, script, arg=None):
        for f in (self.page.frames if self.page else []):
            try:
                r = f.evaluate(script, arg)
            except Exception:
                continue
            if r is not None:
                return r
        return None

    def focused_kind(self):
        """'plain' | 'rich' | None (unknown) for the element that has focus."""
        return self._first_frame_result(_FOCUS_JS)

    def exec_command(self, cmd, value=None):
        """document.execCommand in the focused editable frame (works inside the
        Canvas/TinyMCE iframe, where Google-Docs shortcuts do nothing)."""
        return self._first_frame_result(_EXEC_JS, [cmd, value])

    # ─── Input ───────────────────────────────────────────────────────────────

    def get_clipboard(self):
        return pyperclip.paste()

    def surgical_paste(self, content):
        if self.page:
            self.page.keyboard.insert_text(content)

    def send_char(self, char, dwell_time_seconds):
        if self.page:
            self.page.keyboard.type(char, delay=dwell_time_seconds * 1000)

    def send_backspace(self):
        self.send_key("Backspace")

    def send_shift_enter(self):
        self.send_key("Shift+Enter")

    def send_enter(self):
        self.send_key("Enter")

    def send_tab(self):
        self.send_key("Tab")

    def send_key(self, shortcut):
        """Send a key or shortcut via Playwright (e.g. 'Control+b')."""
        if self.page:
            self.page.keyboard.press(shortcut, delay=10)
