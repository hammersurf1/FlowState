import pyperclip
import time
import threading
from pynput.keyboard import Controller, Key, GlobalHotKeys

class MacDriver:
    def __init__(self):
        self.keyboard = Controller()
        self.hotkey_listener = None
        self._is_blocking = False

    def detect_layout(self):
        return "QWERTY"

    def get_clipboard(self):
        return pyperclip.paste()

    def surgical_paste(self, content):
        saved = pyperclip.paste()
        pyperclip.copy(content)
        with self.keyboard.pressed(Key.cmd):
            self.keyboard.press('v')
            self.keyboard.release('v')
        time.sleep(0.05)
        pyperclip.copy(saved)

    def send_char(self, char, dwell_time):
        self.keyboard.press(char)
        time.sleep(dwell_time)
        self.keyboard.release(char)

    def send_backspace(self):
        self.keyboard.press(Key.backspace)
        self.keyboard.release(Key.backspace)

    def send_shift_enter(self):
        with self.keyboard.pressed(Key.shift):
            self.keyboard.press(Key.enter)
            self.keyboard.release(Key.enter)

    def send_tab(self):
        self.keyboard.press(Key.tab)
        self.keyboard.release(Key.tab)

    def start_blocker(self):
        self._is_blocking = True

    def stop_blocker(self):
        self._is_blocking = False

    def register_hotkeys(self, engine):
        mapping = {
            '<ctrl>+<alt>+v': lambda: threading.Thread(target=engine.trigger_typing, daemon=True).start(),
            # CHANGED: Now requires Shift to be held down as well
            '<ctrl>+<alt>+<shift>+<up>': lambda: engine.cycle_hud(1),
            '<ctrl>+<alt>+<shift>+<down>': lambda: engine.cycle_hud(-1),
            '<ctrl>+<alt>+<shift>+<right>': lambda: engine.adjust_hud(1),
            '<ctrl>+<alt>+<shift>+<left>': lambda: engine.adjust_hud(-1),
            '<esc>': engine.handle_esc
        }
        
        self.hotkey_listener = GlobalHotKeys(mapping)
        self.hotkey_listener.start()