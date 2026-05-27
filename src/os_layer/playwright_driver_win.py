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
        self._cdp = None  # CDP session for raw Input.dispatchKeyEvent

    # ── CDP key dispatch (bypasses Playwright's keyboard API) ────────
    # page.keyboard.press() does not route key events to Google Docs'
    # editor iframe correctly in CDP mode.  We use the raw CDP
    # Input.dispatchKeyEvent method instead, which the browser routes
    # to whichever element has focus (including cross-origin iframes).

    def _ensure_cdp(self):
        """Lazily create a CDP session for the active page."""
        if self._cdp is None and self.page is not None:
            self._cdp = self.context.new_cdp_session(self.page)

    def _cdp_key(self, code, key, type_, modifiers=0, vk=0):
        """Dispatch a single key event via CDP."""
        self._ensure_cdp()
        if self._cdp:
            params = {
                "type": type_,
                "code": code,
                "key": key,
                "modifiers": modifiers,
                "windowsVirtualKeyCode": vk,
            }
            self._cdp.send("Input.dispatchKeyEvent", params)

    def _cdp_press_key(self, combo: str):
        """Send a key combo like 'Backspace', 'Enter', 'Control+b' via CDP.

        Maps keys to their scan codes and dispatches keyDown/keyUp events.
        """
        KEY_MAP = {
            "backspace": ("Backspace", "Backspace", 8),
            "enter": ("Enter", "Enter", 13),
            "tab": ("Tab", "Tab", 9),
            "shift": ("ShiftLeft", "Shift", 16),
            "control": ("ControlLeft", "Control", 17),
            "alt": ("AltLeft", "Alt", 18),
            "escape": ("Escape", "Escape", 27),
            "arrowleft": ("ArrowLeft", "ArrowLeft", 37),
            "arrowright": ("ArrowRight", "ArrowRight", 39),
            " ": ("Space", " ", 32),
        }

        parts = [p.strip() for p in combo.lower().split("+")]
        modifiers = []
        key_part = parts[-1]

        # Separate modifiers from the main key
        for p in parts[:-1]:
            if p in ("control", "ctrl"):
                modifiers.append("control")
            elif p == "shift":
                modifiers.append("shift")
            elif p == "alt":
                modifiers.append("alt")
            elif p == "meta":
                modifiers.append("control")  # Meta maps to Control on Windows

        # Calculate modifiers bitmask
        mod_bits = 0
        if "control" in modifiers:
            mod_bits |= 2
        if "shift" in modifiers:
            mod_bits |= 8
        if "alt" in modifiers:
            mod_bits |= 1

        # Press modifiers
        for mod in modifiers:
            info = KEY_MAP.get(mod)
            if info:
                self._cdp_key(info[0], info[1], "keyDown", mod_bits, info[2])
                time.sleep(0.005)

        # Determine key info
        key_lower = key_part.lower()
        if key_lower in KEY_MAP:
            code, key_name, vk = KEY_MAP[key_lower]
        else:
            # Letter/number/symbol key
            code = f"Key{key_part.upper()}"
            key_name = key_part
            vk = ord(key_part.upper()) if len(key_part) == 1 else 0

        # Recalculate modifiers after modifier keyDowns
        mod_bits = 0
        if "control" in modifiers:
            mod_bits |= 2
        if "shift" in modifiers:
            mod_bits |= 8
        if "alt" in modifiers:
            mod_bits |= 1

        # Press main key
        self._cdp_key(code, key_name, "keyDown", mod_bits, vk)
        time.sleep(0.005)

        # Release main key
        self._cdp_key(code, key_name, "keyUp", mod_bits, vk)

        # Release modifiers (reverse order)
        for mod in reversed(modifiers):
            info = KEY_MAP.get(mod)
            if info:
                self._cdp_key(info[0], info[1], "keyUp", 0, info[2])
                time.sleep(0.005)

    # ── Lifecycle ─────────────────────────────────────────────────

    def attach(self, window_title=None):
        if self.browser:
            self._ensure_active_page(window_title)
            return
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
        self._cdp = None  # reset CDP session for new page

    def detach(self):
        print("Detaching from Chrome...")
        if self._cdp:
            try:
                self._cdp.detach()
            except Exception:
                pass
            self._cdp = None
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
            subprocess.run(["taskkill", "/IM", "chrome.exe"], capture_output=True, timeout=15)
            for _ in range(10):
                time.sleep(0.5)
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq chrome.exe"],
                    capture_output=True, text=True, timeout=10
                )
                if "chrome.exe" not in result.stdout.lower():
                    break
            else:
                print("Force-killing Chrome...")
                subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True, timeout=15)
                time.sleep(1)
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

        for page in self.context.pages:
            if safe_eval(page, "document.hasFocus()"):
                self.page = page
                self.page.bring_to_front()
                return

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

        for page in self.context.pages:
            if safe_eval(page, "document.visibilityState === 'visible'"):
                self.page = page
                self.page.bring_to_front()
                return

        if self.context.pages:
            self.page = self.context.pages[-1]
            self.page.bring_to_front()

        if not self.page:
            raise Exception("No browser tabs found!")

    # ── Page helpers ──────────────────────────────────────────────

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

    def is_google_docs(self):
        try:
            if self.page:
                return "docs.google.com/document" in self.page.url
        except Exception:
            pass
        return False

    # ── Text insertion (uses Playwright — works fine) ─────────────

    def surgical_paste(self, content):
        if self.page:
            self.page.keyboard.insert_text(content)

    def send_char(self, char, dwell_time_seconds):
        if self.page:
            self.page.keyboard.insert_text(char)

    # ── Key operations (ALL use CDP now, not Playwright) ──────────

    def send_backspace(self):
        if self.page:
            self._cdp_press_key("Backspace")

    def send_shift_enter(self):
        if self.page:
            self._cdp_press_key("Shift+Enter")

    def send_enter(self):
        if self.page:
            self._cdp_press_key("Enter")

    def send_tab(self):
        if self.page:
            self._cdp_press_key("Tab")

    def send_key(self, shortcut):
        """Send a keyboard shortcut via CDP (e.g. 'Control+b')."""
        if self.page:
            self._cdp_press_key(shortcut)
            time.sleep(0.05)

    def send_formatting_key(self, key):
        """Send a formatting keystroke via CDP (Ctrl+B, Ctrl+I, etc.)."""
        if self.page:
            self._cdp_press_key(key)
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
            time.sleep(0.05)
