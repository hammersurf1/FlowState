import pyperclip
import ctypes
import os
import subprocess
import time


class PlaywrightDriverWin:
    def __init__(self, playwright_instance):
        self.p = playwright_instance
        self.browser = None
        self.context = None
        self.page = None

    def attach(self, window_title=None):
        if self.browser:
            # Already attached - just re-acquire the correct page
            self._ensure_active_page(window_title)
            return
        # Dynamically connect only when typing begins
        print("Attaching to Chrome on port 9225...")
        try:
            self.browser = self.p.chromium.connect_over_cdp('http://localhost:9225')
        except Exception:
            print("Not found. Attempting to relaunch Chrome with debugging port...")
            if self._auto_launch_chrome():
                time.sleep(4)
                try:
                    self.browser = self.p.chromium.connect_over_cdp('http://localhost:9225')
                except Exception:
                    raise Exception(
                        "Failed to connect to Chrome on debugging port 9225 after relaunch. "
                        "Chrome may have crashed or the port may be blocked by another process."
                    )
            else:
                raise Exception("Could not find Google Chrome installed.")

        self.context = self.browser.contexts[0]
        self._ensure_active_page(window_title)

    def detach(self):
        # Sever the connection completely when typing finishes
        print("Detaching from Chrome...")
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
            self.context = None
            self.page = None

    def _auto_launch_chrome(self):
        paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
        ]

        chrome_exe = None
        for p in paths:
            if os.path.exists(p):
                chrome_exe = p
                break

        if not chrome_exe:
            return False

        # Check if Chrome is already running
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                capture_output=True, text=True, timeout=10
            )
            chrome_was_running = "chrome.exe" in result.stdout.lower()
        except Exception:
            chrome_was_running = False

        if chrome_was_running:
            print("Chrome is running. Closing it to reopen with debugging port...")
            # Graceful shutdown
            subprocess.run(
                ["taskkill", "/IM", "chrome.exe"],
                capture_output=True, timeout=15
            )
            # Wait up to 5 seconds for graceful exit
            for _ in range(10):
                time.sleep(0.5)
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                    capture_output=True, text=True, timeout=10
                )
                if "chrome.exe" not in result.stdout.lower():
                    break
            else:
                # Force kill
                print("Force-killing Chrome...")
                subprocess.run(
                    ["taskkill", "/F", "/IM", "chrome.exe"],
                    capture_output=True, timeout=15
                )
                time.sleep(1)

        # Launch Chrome with the user's real default profile + debugging port.
        # No --user-data-dir so it uses %LOCALAPPDATA%\Google\Chrome\User Data
        # --restore-last-session ensures tabs come back after the unclean shutdown.
        subprocess.Popen([
            chrome_exe,
            "--remote-debugging-port=9225",
            "--restore-last-session"
        ])
        return True

    def _ensure_active_page(self, window_title=None):
        def safe_eval(page, script):
            for _ in range(3):
                try:
                    return page.evaluate(script)
                except Exception:
                    time.sleep(0.1)
            return False

        # STRATEGY 1: Match by window title (most reliable - captured at hotkey press time).
        # Chrome window title format: "<Page Title> - Google Chrome"
        # Strip the " - Google Chrome" suffix to get the raw page title.
        if window_title:
            page_title_hint = window_title.replace(" - Google Chrome", "").strip()
            if page_title_hint:
                print(f"Looking for tab matching title: '{page_title_hint}'")
                for page in self.context.pages:
                    try:
                        if (page_title_hint.lower() in page.title().lower()
                                or page.title().lower() in page_title_hint.lower()):
                            self.page = page
                            self.page.bring_to_front()
                            print(f"Matched tab by title: '{page.title()}'")
                            return
                    except Exception:
                        pass

        # STRATEGY 2: document.hasFocus() - works if CDP connection was fast
        for page in self.context.pages:
            if safe_eval(page, "document.hasFocus()"):
                self.page = page
                self.page.bring_to_front()
                return

        # STRATEGY 3: Visible page with an active text input
        for page in self.context.pages:
            if safe_eval(page, (
                "document.visibilityState === 'visible' && document.activeElement && "
                "(document.activeElement.tagName === 'TEXTAREA' || "
                "document.activeElement.tagName === 'INPUT' || "
                "document.activeElement.isContentEditable)"
            )):
                self.page = page
                self.page.bring_to_front()
                return

        # STRATEGY 4: Any visible page
        for page in self.context.pages:
            if safe_eval(page, "document.visibilityState === 'visible'"):
                self.page = page
                self.page.bring_to_front()
                return

        # STRATEGY 5: Last resort - most recently opened tab
        if self.context.pages:
            self.page = self.context.pages[-1]
            self.page.bring_to_front()

        if not self.page:
            raise Exception("No browser tabs found! Playwright cannot type into a closed browser.")

    def focus_page(self):
        if self.page:
            try:
                self.page.bring_to_front()
            except Exception:
                pass

    def detect_layout(self):
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
            klid = user32.GetKeyboardLayout(thread_id)
            lang_id = klid & 0xFFFF
            if lang_id == 0x0407:
                return "QWERTZ"
            if lang_id == 0x040C:
                return "AZERTY"
        except Exception:
            pass
        return "QWERTY"

    def get_clipboard(self):
        return pyperclip.paste()

    def surgical_paste(self, content):
        if self.page:
            self.page.keyboard.insert_text(content)

    def send_char(self, char, dwell_time_seconds):
        """Atomic text insertion — never drops characters, even at high speed."""
        if self.page:
            self.page.keyboard.insert_text(char)

    def send_backspace(self):
        if self.page:
            self.page.keyboard.press("Backspace", delay=10)

    def send_shift_enter(self):
        if self.page:
            self.page.keyboard.press("Shift+Enter", delay=10)

    def send_enter(self):
        if self.page:
            self.page.keyboard.press("Enter", delay=10)

    def send_tab(self):
        if self.page:
            self.page.keyboard.press("Tab", delay=10)

    def send_key(self, shortcut):
        """Send an arbitrary keyboard shortcut via Playwright (e.g. 'Control+b')."""
        if self.page:
            self.page.keyboard.press(shortcut, delay=10)
