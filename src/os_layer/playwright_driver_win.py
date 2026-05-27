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
        self._cdp = None  # CDP session

    def _focus_editor(self):
        """Click into the Google Docs editor to ensure keyboard focus."""
        if not self.page:
            return
        try:
            # Click into the editor area — Google Docs has a 
            # .docs-texteventtarget-iframe that receives keyboard input
            self.page.evaluate('''
                (() => {
                    const iframe = document.querySelector('.docs-texteventtarget-iframe');
                    if (iframe) {
                        iframe.focus();
                        iframe.contentWindow.focus();
                    }
                    // Also click the main editing surface
                    const surface = document.querySelector('.kix-appview-editor');
                    if (surface) surface.click();
                })()
            ''')
            time.sleep(0.02)
        except Exception:
            pass

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

    def detach(self):
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

    # ── Text insertion ───────────────────────────────────────────

    def surgical_paste(self, content):
        if self.page:
            self.page.keyboard.insert_text(content)

    def send_char(self, char, dwell_time_seconds):
        if self.page:
            self.page.keyboard.insert_text(char)

    # ── Key operations ───────────────────────────────────────────
    # Focus the editor before every key press to ensure Google Docs
    # iframe receives keyboard events.

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
        self._dispatch_key(shortcut)

    def send_formatting_key(self, key):
        self._dispatch_key(key)

    # -- CDP Key Dispatch --
    #
    # Google Docs captures keyboard shortcuts at the top-level
    # document, not inside the .docs-texteventtarget-iframe.
    # CDP Input.dispatchKeyEvent dispatches at page level where
    # Google Docs' global shortcut handler picks it up.

    def _get_cdp(self):
        """Get or create a CDP session for dispatching key events."""
        if self._cdp is None and self.page:
            self._cdp = self.page.context.new_cdp_session(self.page)
        return self._cdp

    def _release_cdp(self):
        """Detach CDP session when done typing."""
        if self._cdp is not None:
            try:
                self._cdp.detach()
            except Exception:
                pass
            self._cdp = None

    def _dispatch_key(self, chord):
        """Send a key chord via CDP Input.dispatchKeyEvent.

        Args:
            chord: Playwright-style chord string e.g. "Control+b",
                   "Control+Alt+2", "Enter", "Shift+Enter", "Tab".
        """
        if not self.page:
            return

        cdp = self._get_cdp()
        if cdp is None:
            return

        parts = [p.strip() for p in chord.split("+")]

        # Separate modifiers from the main key
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

        # KeyDown for each modifier
        for mod_code, mod_key, mod_vk, mod_bit in modifiers:
            mod_bits |= mod_bit
            cdp.send("Input.dispatchKeyEvent", {
                "type": "keyDown",
                "code": mod_code,
                "key": mod_key,
                "modifiers": mod_bits,
                "windowsVirtualKeyCode": mod_vk,
            })

        # KeyDown + KeyUp for main key
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

        # KeyUp for each modifier (reverse order)
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

    def paste_html(self, html):
        """Put HTML on the Windows clipboard and trigger Ctrl+V.
        
        Google Docs ignores DOM manipulation but handles clipboard
        paste events natively, creating proper tables and formatting.
        """
        import ctypes
        import ctypes.wintypes

        kernel32 = ctypes.windll.kernel32
        user32 = ctypes.windll.user32

        CF_UNICODETEXT = 13

        # Register CF_HTML format
        cf_html = user32.RegisterClipboardFormatW("HTML Format")
        if not cf_html:
            return

        # Build CF_HTML payload with required header
        html_body = html
        # Wrap in minimal HTML document for clipboard
        fragment = f"""<html><body>\n<!--StartFragment-->{html_body}<!--EndFragment-->\n</body></html>"""
        # CF_HTML header with byte offsets
        header_template = (
            "Version:0.9\r\n"
            "StartHTML:{start_html:010d}\r\n"
            "EndHTML:{end_html:010d}\r\n"
            "StartFragment:{start_frag:010d}\r\n"
            "EndFragment:{end_frag:010d}\r\n"
        )
        # Calculate with placeholder lengths
        dummy_header = header_template.format(
            start_html=0, end_html=0, start_frag=0, end_frag=0
        )
        header_len = len(dummy_header.encode("utf-8"))
        frag_bytes = fragment.encode("utf-8")
        start_html = header_len
        end_html = header_len + len(frag_bytes)
        start_frag = header_len + frag_bytes.find(b"<!--StartFragment-->") + len(b"<!--StartFragment-->")
        end_frag = header_len + frag_bytes.find(b"<!--EndFragment-->")

        real_header = header_template.format(
            start_html=start_html,
            end_html=end_html,
            start_frag=start_frag,
            end_frag=end_frag,
        )
        cf_html_bytes = real_header.encode("utf-8") + frag_bytes + b"\x00"

        # Plain text fallback (strip HTML tags for CF_UNICODETEXT)
        import re as _re
        plain = _re.sub(r'<[^>]+>', '', html_body)
        plain_utf16 = plain.encode("utf-16-le") + b"\x00\x00"

        # Set clipboard contents
        if not user32.OpenClipboard(0):
            return
        try:
            user32.EmptyClipboard()

            # Set CF_HTML
            h_html = kernel32.GlobalAlloc(0x0002, len(cf_html_bytes))  # GMEM_MOVEABLE
            if h_html:
                kernel32.GlobalLock.restype = ctypes.c_void_p
                p = kernel32.GlobalLock(h_html)
                if p:
                    ctypes.memmove(p, cf_html_bytes, len(cf_html_bytes))
                    kernel32.GlobalUnlock(h_html)
                    user32.SetClipboardData(cf_html, h_html)

            # Set CF_UNICODETEXT
            h_text = kernel32.GlobalAlloc(0x0002, len(plain_utf16))
            if h_text:
                kernel32.GlobalLock.restype = ctypes.c_void_p
                p = kernel32.GlobalLock(h_text)
                if p:
                    ctypes.memmove(p, plain_utf16, len(plain_utf16))
                    kernel32.GlobalUnlock(h_text)
                    user32.SetClipboardData(CF_UNICODETEXT, h_text)
        finally:
            user32.CloseClipboard()

        # Trigger native paste via Ctrl+V through CDP
        self._focus_editor()
        time.sleep(0.05)
        self._dispatch_key("Control+v")
        time.sleep(0.3)  # Give Google Docs time to process the paste


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
