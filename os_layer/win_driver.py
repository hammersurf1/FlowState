import keyboard
import pyperclip
import ctypes
import time
import threading

class WinDriver:
    def __init__(self):
        self._block_hook = None
        self.esc_handler = None # Store the reference to engine.handle_esc

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
        # We define which keys are allowed to pass through the suppression
        allowed = ['esc', 'ctrl', 'left ctrl', 'right ctrl', 
                   'shift', 'left shift', 'right shift', 
                   'alt', 'left alt', 'right alt', 
                   'up', 'down', 'left', 'right']
                   
        def block_event(e):
            # FIX: Manually trigger the ESC handler if ESC is pressed 
            # while the blocker is active. This is more reliable than add_hotkey.
            if e.name.lower() == 'esc' and e.event_type == 'down':
                if self.esc_handler:
                    # Execute handler in a thread to avoid blocking the hook
                    threading.Thread(target=self.esc_handler, daemon=True).start()
            
            return e.name.lower() in allowed
        
        self._block_hook = keyboard.hook(block_event, suppress=True)
        
        # Ensure modifiers are released so they don't "stick" when blocking starts
        for mod in ['ctrl', 'alt', 'shift', 'windows']:
            keyboard.release(mod)

    def stop_blocker(self):
        if self._block_hook:
            keyboard.unhook(self._block_hook)
            self._block_hook = None

    def register_hotkeys(self, engine):
        # Store the engine's escape handler for use in start_blocker
        self.esc_handler = engine.handle_esc

        keyboard.add_hotkey('ctrl+alt+v', lambda: threading.Thread(target=engine.trigger_typing, daemon=True).start())
        
        keyboard.add_hotkey('ctrl+alt+shift+up', lambda: engine.cycle_hud(1))
        keyboard.add_hotkey('ctrl+alt+shift+down', lambda: engine.cycle_hud(-1))
        keyboard.add_hotkey('ctrl+alt+shift+right', lambda: engine.adjust_hud(1))
        keyboard.add_hotkey('ctrl+alt+shift+left', lambda: engine.adjust_hud(-1))
        
        # Keep this for when the blocker is NOT running
        keyboard.add_hotkey('esc', engine.handle_esc)