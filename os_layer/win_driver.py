import keyboard
import pyperclip
import ctypes
import time
import threading

class WinDriver:
    def __init__(self):
        self._block_hook = None

    def detect_layout(self):
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        thread_id = user32.GetWindowThreadProcessId(hwnd, 0)
        klid = user32.GetKeyboardLayout(thread_id)
        lang_id = klid & 0xFFFF
        
        if lang_id == 0x0407: return "QWERTZ"
        if lang_id == 0x040C: return "AZERTY"
        return "QWERTY"

    def get_clipboard(self):
        return pyperclip.paste()

    def surgical_paste(self, content):
        saved = pyperclip.paste()
        pyperclip.copy(content)
        
        # Failsafe: Ensure modifiers are completely clear before pasting
        for mod in['ctrl', 'shift', 'alt', 'windows']:
            keyboard.release(mod)
            
        keyboard.send("ctrl+v")
        time.sleep(0.05)
        pyperclip.copy(saved)

    def send_char(self, char, dwell_time):
        # keyboard.write is significantly more stable on Windows than press/release
        # for preserving uppercase and symbols without getting tangled in modifier states.
        keyboard.write(char)
        # We sleep afterwards to maintain the exact same overall human rhythm and delay
        time.sleep(dwell_time)

    def send_backspace(self):
        keyboard.send("backspace")

    def send_shift_enter(self):
        keyboard.send("shift+enter")

    def send_tab(self):
        keyboard.send("tab")

    def start_blocker(self):
        allowed = ['esc', 'alt', 'up', 'down', 'left', 'right']
        def block_event(e):
            return e.name.lower() in allowed
        
        # 1. Engage the keyboard lock
        self._block_hook = keyboard.hook(block_event, suppress=True)
        
        # 2. THE STUCK MODIFIER FIX:
        # Force release all modifiers immediately. If the user released these keys 
        # AFTER the hook activated, Windows missed it. We force the OS to reset them here.
        for mod in['ctrl', 'left ctrl', 'right ctrl', 
                    'alt', 'left alt', 'right alt', 
                    'shift', 'left shift', 'right shift', 
                    'windows', 'left windows', 'right windows']:
            keyboard.release(mod)

    def stop_blocker(self):
        if self._block_hook:
            keyboard.unhook(self._block_hook)
            self._block_hook = None

    def register_hotkeys(self, engine):
        keyboard.add_hotkey('ctrl+alt+v', lambda: threading.Thread(target=engine.trigger_typing, daemon=True).start())
        keyboard.add_hotkey('alt+up', lambda: engine.cycle_hud(1))
        keyboard.add_hotkey('alt+down', lambda: engine.cycle_hud(-1))
        keyboard.add_hotkey('alt+right', lambda: engine.adjust_hud(1))
        keyboard.add_hotkey('alt+left', lambda: engine.adjust_hud(-1))
        keyboard.add_hotkey('esc', engine.handle_esc)