import pyperclip
import os
import subprocess
import time


class PlaywrightDriverMac:
    def __init__(self, playwright_instance):
        self.p = playwright_instance
        self.browser = None
        self.context = None
        self.page = None
        self._cdp = None  # CDP session

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
        self._release_cdp()
        if self.browser:
            try:
                self.browser.close()
            except Exception:
                pass
            self.browser = None
            self.context = None
            self.page = None

    def _auto_launch_chrome(self):
        chrome_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        if not os.path.exists(chrome_path):
            return False

        # Check if Chrome is already running
        try:
            result = subprocess.run(
                ["pgrep", "-x", "Google Chrome"],
                capture_output=True, text=True, timeout=5
            )
            chrome_was_running = result.returncode == 0 and result.stdout.strip()
        except Exception:
            chrome_was_running = False

        if chrome_was_running:
            print("Chrome is running. Closing it to reopen with debugging port...")
            # Graceful shutdown
            subprocess.run(
                ["killall", "-TERM", "Google Chrome"],
                capture_output=True, timeout=10
            )
            # Wait up to 5 seconds for graceful exit
            for _ in range(10):
                time.sleep(0.5)
                result = subprocess.run(
                    ["pgrep", "-x", "Google Chrome"],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode != 0 or not result.stdout.strip():
                    break
            else:
                # Force kill
                print("Force-killing Chrome...")
                subprocess.run(
                    ["killall", "-9", "Google Chrome"],
                    capture_output=True, timeout=10
                )
                time.sleep(1)

        # Launch Chrome with the user's real default profile + debugging port.
        # No --user-data-dir so it uses ~/Library/Application Support/Google/Chrome
        # --restore-last-session ensures tabs come back after the unclean shutdown.
        subprocess.Popen([
            chrome_path,
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
        # Chrome window title format on macOS: "<Page Title>" (no suffix like Windows).
        # Some versions may append " - Google Chrome", so strip it just in case.
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
        """Detect keyboard layout on macOS via system defaults."""
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleCurrentKeyboardLayoutInputSourceID"],
                capture_output=True, text=True, timeout=5
            )
            layout_id = result.stdout.strip().lower()
            if "german" in layout_id or "qwertz" in layout_id:
                return "QWERTZ"
            if "french" in layout_id or "azerty" in layout_id:
                return "AZERTY"
        except Exception:
            pass
        return "QWERTY"

    @staticmethod
    def get_frontmost_window_title():
        """Use AppleScript to get the title of the frontmost window (for tab matching)."""
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first window '
                 'of (first application process whose frontmost is true)'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""

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
        self._dispatch_key("Backspace")

    def send_shift_enter(self):
        self._dispatch_key("Shift+Enter")

    def send_enter(self):
        self._dispatch_key("Enter")

    def send_tab(self):
        self._dispatch_key("Tab")


    def send_formatting_key(self, key):
        """Send a formatting keystroke via Playwright (Ctrl+B, Ctrl+I, etc.)."""
        self._dispatch_key(key)

    # -- Editor focus --

    def _focus_editor(self):
        """Click into the Google Docs editor to ensure keyboard focus."""
        if not self.page:
            return
        try:
            self.page.evaluate("""
                (() => {
                    const iframe = document.querySelector('.docs-texteventtarget-iframe');
                    if (iframe) {
                        iframe.focus();
                        iframe.contentWindow.focus();
                    }
                    const surface = document.querySelector('.kix-appview-editor');
                    if (surface) surface.click();
                })()
            """)
            time.sleep(0.02)
        except Exception:
            pass

    # -- CDP Key Dispatch --

    def _get_cdp(self):
        if self._cdp is None and self.page:
            self._cdp = self.page.context.new_cdp_session(self.page)
        return self._cdp

    def _release_cdp(self):
        if self._cdp is not None:
            try:
                self._cdp.detach()
            except Exception:
                pass
            self._cdp = None

    def _dispatch_key(self, chord):
        if not self.page:
            return
        cdp = self._get_cdp()
        if cdp is None:
            return
        parts = [p.strip() for p in chord.split("+")]
        modifiers = []
        main_key = None
        for part in parts:
            part_lower = part.lower()
            mi = _MODIFIER_MAP.get(part_lower)
            if mi:
                modifiers.append(mi)
            else:
                main_key = part
        if main_key is None:
            main_key = parts[-1]
        key_info = _KEY_MAP.get(main_key)
        if key_info is None:
            if len(main_key) == 1:
                code = "Key" + main_key.upper()
                vk = ord(main_key.upper())
                key_info = (code, main_key.lower(), vk)
            else:
                key_info = (main_key, main_key, 0)
        code, key, vk = key_info
        mod_bits = 0
        for mod_code, mod_key, mod_vk, mod_bit in modifiers:
            mod_bits |= mod_bit
            cdp.send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "code": mod_code,
                "key": mod_key,
                "modifiers": mod_bits,
                "windowsVirtualKeyCode": mod_vk,
            })
        cdp.send("Input.dispatchKeyEvent", {
            "type": "keyDown",
            "code": code,
            "key": key,
            "modifiers": mod_bits,
            "windowsVirtualKeyCode": vk,
        })
        cdp.send("Input.dispatchKeyEvent", {
            "type": "keyUp",
            "code": code,
            "key": key,
            "modifiers": mod_bits,
            "windowsVirtualKeyCode": vk,
        })
        for mod_code, mod_key, mod_vk, mod_bit in reversed(modifiers):
            mod_bits &= ~mod_bit
            cdp.send("Input.dispatchKeyEvent", {
                "type": "keyUp",
                "code": mod_code,
                "key": mod_key,
                "modifiers": mod_bits,
                "windowsVirtualKeyCode": mod_vk,
            })
        time.sleep(0.05)

    def inject_html(self, html):
        """Inject raw HTML at the cursor position (used for tables, HR)."""
        if self.page:
            escaped = html.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "\\n")
            self.page.evaluate(f'''
                (() => {{
                    const sel = window.getSelection();
                    if (sel.rangeCount) {{
                        const r = sel.getRangeAt(0);
                        r.deleteContents();
                        const frag = r.createContextualFragment('{escaped}');
                        r.insertNode(frag);
                        r.collapse(false);
                    }}
                }})()
            ''')

    def is_google_docs(self):
        """True if the active page is a Google Docs document."""
        try:
            if self.page:
                return "docs.google.com/document" in self.page.url
        except Exception:
            pass
        return False

    def send_key(self, shortcut):
        """Send an arbitrary keyboard shortcut via Playwright (e.g. 'Meta+b')."""
        self._dispatch_key(shortcut)


# -- Key map for CDP dispatch --

_KEY_MAP = {
    "b": ("KeyB", "b", 66), "i": ("KeyI", "i", 73),
    "u": ("KeyU", "u", 85), "a": ("KeyA", "a", 65),
    "c": ("KeyC", "c", 67), "k": ("KeyK", "k", 75),
    "v": ("KeyV", "v", 86), "x": ("KeyX", "x", 88),
    "y": ("KeyY", "y", 89), "z": ("KeyZ", "z", 90),
    "0": ("Digit0", "0", 48), "1": ("Digit1", "1", 49),
    "2": ("Digit2", "2", 50), "3": ("Digit3", "3", 51),
    "4": ("Digit4", "4", 52), "5": ("Digit5", "5", 53),
    "6": ("Digit6", "6", 54), "7": ("Digit7", "7", 55),
    "8": ("Digit8", "8", 56), "9": ("Digit9", "9", 57),
    "Enter": ("Enter", "Enter", 13),
    "Backspace": ("Backspace", "Backspace", 8),
    "Tab": ("Tab", "Tab", 9),
    "Escape": ("Escape", "Escape", 27),
    "ArrowUp": ("ArrowUp", "ArrowUp", 38),
    "ArrowDown": ("ArrowDown", "ArrowDown", 40),
    "ArrowLeft": ("ArrowLeft", "ArrowLeft", 37),
    "ArrowRight": ("ArrowRight", "ArrowRight", 39),
    " ": ("Space", " ", 32),
}

_MODIFIER_MAP = {
    "control": ("ControlLeft", "Control", 17, 2),
    "ctrl": ("ControlLeft", "Control", 17, 2),
    "alt": ("AltLeft", "Alt", 18, 1),
    "shift": ("ShiftLeft", "Shift", 16, 8),
    "meta": ("MetaLeft", "Meta", 91, 4),
    "cmd": ("MetaLeft", "Meta", 91, 4),
}
