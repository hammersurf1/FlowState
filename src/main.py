import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import sys
import threading
import queue
import keyboard
import ctypes
from playwright.sync_api import sync_playwright

from engine import TypingEngine
from os_layer.playwright_driver import PlaywrightDriver

def create_image(color):
    """Generates a clean 64x64 colored circle to represent state"""
    image = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill=color, outline="white", width=3)
    return image

class MainApp:
    def __init__(self):
        self.pw_queue = queue.Queue()
        self.engine = None
        self.tray_icon = None

    def start(self):
        # Boot Playwright on a strict background thread to prevent thread conflicts
        threading.Thread(target=self.playwright_worker, daemon=True).start()
        
        # Setup System Tray (Must be on main thread)
        self.tray_icon = pystray.Icon("AutoTyper", create_image("#0078D7"), "AutoTyper: Starting...")
        self.tray_icon.menu = pystray.Menu(item("Starting up...", lambda: None, enabled=False))
        
        print("AutoTyper starting... look for the system tray icon.")
        self.tray_icon.run()

    def update_tray(self):
        if not self.engine or not self.tray_icon: return
        
        try:
            var_name = self.engine.settings_list[self.engine.current_setting_index]
            val = self.engine.settings[var_name]
            friendly = self.engine.setting_names[self.engine.current_setting_index]
            
            color = "#0078D7" 
            status_text = "Idle"
            
            if self.engine.is_running and self.engine.countdown > 0:
                color = "#FFB900" 
                status_text = f"Starting in {self.engine.countdown}..."
            elif self.engine.is_running and not self.engine.is_paused:
                color = "#107C10" 
                status_text = "Running"
            elif self.engine.is_paused:
                color = "#D83B01" 
                status_text = "Paused"
                
            self.tray_icon.icon = create_image(color)
            self.tray_icon.title = f"AutoTyper ({status_text})\n{friendly}: {val}"

            menu_items =[]
            menu_items.append(item(f"Status: {status_text}", lambda: None, enabled=False))
            menu_items.append(item("---", lambda: None, enabled=False))

            for i, v_name in enumerate(self.engine.settings_list):
                f_name = self.engine.setting_names[i]
                c_val = self.engine.settings[v_name]
                prefix = "▶ " if i == self.engine.current_setting_index else "  "
                menu_items.append(item(f"{prefix}{f_name}: {c_val}", lambda: None, enabled=False))

            menu_items.append(item("---", lambda: None, enabled=False))
            menu_items.append(item("Exit AutoTyper", self.exit_app))
            
            # Using self.tray_icon.menu assignment from a background thread can hang
            # if done too rapidly (like during countdown).
            if self.engine.countdown == 0 and not getattr(self, '_updating_menu', False):
                self._updating_menu = True
                self.tray_icon.menu = pystray.Menu(*menu_items)
                self._updating_menu = False
                
        except Exception as e:
            print(f"Tray Update Error: {e}")

    def exit_app(self):
        self.tray_icon.stop()
        sys.exit(0)

    def playwright_worker(self):
        try:
            with sync_playwright() as p:
                driver = PlaywrightDriver(p)
                self.engine = TypingEngine(driver)
                
                # Bind UI callbacks
                self.engine.ui_update_callback = self.update_tray
                self.engine.status_callback = self.update_tray
                self.update_tray()

                # Register Hotkeys to directly update state when possible
                def on_trigger():
                    if self.engine.is_running:
                        self.engine.set_state(paused=not self.engine.is_paused)
                    else:
                        # Snapshot the active window title RIGHT NOW before anything else runs.
                        # Chrome always sets its window title to "<Page Title> - Google Chrome".
                        # We capture this here (on the hotkey thread) so Playwright can match
                        # the exact tab after connecting, regardless of focus changes.
                        buf = ctypes.create_unicode_buffer(512)
                        ctypes.windll.user32.GetWindowTextW(
                            ctypes.windll.user32.GetForegroundWindow(), buf, 512
                        )
                        window_title = buf.value
                        self.pw_queue.put(("trigger_typing", window_title))

                keyboard.add_hotkey('ctrl+alt+v', on_trigger)
                keyboard.add_hotkey('ctrl+alt+shift+up', lambda: self.engine.cycle_hud(1))
                keyboard.add_hotkey('ctrl+alt+shift+down', lambda: self.engine.cycle_hud(-1))
                keyboard.add_hotkey('ctrl+alt+shift+right', lambda: self.engine.adjust_hud(1))
                keyboard.add_hotkey('ctrl+alt+shift+left', lambda: self.engine.adjust_hud(-1))
                keyboard.add_hotkey('esc', self.engine.handle_esc)

                # Infinite task loop
                while True:
                    action, arg = self.pw_queue.get()
                    try:
                        if action == "trigger_typing":
                            self.engine.trigger_typing(arg)
                        elif action == "cycle_hud":
                            self.engine.cycle_hud(arg)
                        elif action == "adjust_hud":
                            self.engine.adjust_hud(arg)
                        elif action == "handle_esc":
                            self.engine.handle_esc()
                    except Exception as e:
                        print(f"Action Error ({action}): {e}")
                        self.engine.driver.detach()
                        self.engine.set_state(running=False, paused=False)
                        
        except Exception as e:
            print(f"Playwright Worker Critical Error: {e}")

if __name__ == "__main__":
    app = MainApp()
    app.start()