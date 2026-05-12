import pyperclip
import ctypes
import sys
import os
import subprocess
import time

class PlaywrightDriver:
    def __init__(self, playwright_instance):
        self.p = playwright_instance
        self.browser = None
        self.context = None
        self.page = None

    def attach(self):
        if self.browser:
            return
        # Dynamically connect only when typing begins
        print("Attaching to Stealth Chrome on port 9225...")
        try:
            self.browser = self.p.chromium.connect_over_cdp('http://localhost:9225')
        except Exception:
            print("Not found. Attempting to auto-launch Chrome...")
            if self._auto_launch_chrome():
                time.sleep(3)
                try:
                    self.browser = self.p.chromium.connect_over_cdp('http://localhost:9225')
                except Exception:
                    raise Exception("Failed to open debugging port. If Chrome is already running, you MUST completely close it or launch it with --remote-debugging-port=9225 first!")
            else:
                raise Exception("Could not find Google Chrome installed.")
        
        self.context = self.browser.contexts[0]
        self._ensure_active_page()

    def detach(self):
        # Sever the connection completely when typing finishes
        print("Detaching from Chrome...")
        if self.browser:
            try:
                self.browser.disconnect()
            except Exception:
                pass
            self.browser = None
            self.context = None
            self.page = None

    def _auto_launch_chrome(self):
        paths =[
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
            
        profile_dir = r"C:\chrome-stealth-profile"
        subprocess.Popen([
            chrome_exe,
            "--remote-debugging-port=9225",
            f"--user-data-dir={profile_dir}"
        ])
        return True

    def _ensure_active_page(self):
        # First try to find the page that actively has focus
        for page in self.context.pages:
            try:
                if page.evaluate("document.hasFocus()"):
                    self.page = page
                    self.page.bring_to_front()
                    return
            except Exception:
                pass
                
        # Fallback to the first visible page if none have focus
        for page in self.context.pages:
            try:
                if page.evaluate("document.visibilityState === 'visible'"):
                    self.page = page
                    self.page.bring_to_front()
                    return
            except Exception:
                pass
        
        # Fallback to the first page available
        if self.context.pages:
            self.page = self.context.pages[0]
            
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
            if lang_id == 0x0407: return "QWERTZ"
            if lang_id == 0x040C: return "AZERTY"
        except:
            pass
        return "QWERTY"

    def get_clipboard(self):
        return pyperclip.paste()

    def surgical_paste(self, content):
        if self.page:
            self.page.keyboard.insert_text(content)

    def send_char(self, char, dwell_time_seconds):
        if self.page:
            delay_ms = dwell_time_seconds * 1000
            self.page.keyboard.type(char, delay=delay_ms)

    def send_backspace(self):
        if self.page:
            self.page.keyboard.press("Backspace", delay=10)

    def send_shift_enter(self):
        if self.page:
            self.page.keyboard.press("Shift+Enter", delay=10)

    def send_tab(self):
        if self.page:
            self.page.keyboard.press("Tab", delay=10)