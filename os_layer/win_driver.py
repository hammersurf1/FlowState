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
        
        for mod in ['ctrl', 'shift', 'alt', 'windows']:
            keyboard.release(mod)
            
        keyboard.send("ctrl+v")
        time.sleep(0.05)
        pyperclip.copy(saved)

    def send_char(self, char, dwell_time):
        keyboard.write(char)
        time.sleep(dwell_time)

    def send_backspace(self):
        keyboard.send("backspace")

    def send_shift_enter(self):
        keyboard.send("shift+enter")

    def send_tab(self):
        keyboard.send("tab")

    def start_blocker(self):
        # Allow our new 3-modifier combination through the lock
        allowed =['esc', 'ctrl', 'left ctrl', 'right ctrl', 
                   'shift', 'left shift', 'right shift', 
                   'alt', 'left alt', 'right alt', 
                   'up', 'down', 'left', 'right']
                   
        def block_event(e):
            return e.name.lower() in allowed
        
        self._block_hook = keyboard.hook(block_event, suppress=True)
        
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
        
        # CHANGED: Now requires Shift to be held down as well
        keyboard.add_hotkey('ctrl+alt+shift+up', lambda: engine.cycle_hud(1))
        keyboard.add_hotkey('ctrl+alt+shift+down', lambda: engine.cycle_hud(-1))
        keyboard.add_hotkey('ctrl+alt+shift+right', lambda: engine.adjust_hud(1))
        keyboard.add_hotkey('ctrl+alt+shift+left', lambda: engine.adjust_hud(-1))
        
        keyboard.add_hotkey('esc', engine.handle_esc)