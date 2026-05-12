"""
FlowState — macOS Entry Point
Launches the system tray app with the Playwright-based typing engine.
Uses the `pynput` library for global hotkeys (requires Accessibility permission on macOS).
"""

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import sys
import threading
import queue
from pynput import keyboard as pynput_keyboard
from playwright.sync_api import sync_playwright

from engine import TypingEngine
from os_layer.playwright_driver_mac import PlaywrightDriverMac


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
        self._hotkey_listener = None

    def start(self):
        # Boot Playwright on a strict background thread to prevent thread conflicts
        threading.Thread(target=self.playwright_worker, daemon=True).start()

        # Setup System Tray (Must be on main thread for macOS)
        self.tray_icon = pystray.Icon("FlowState", create_image("#0078D7"), "FlowState: Starting...")
        self.tray_icon.menu = pystray.Menu(item("Starting up...", lambda: None, enabled=False))

        print("FlowState starting... look for the menu bar icon.")
        self.tray_icon.run()

    def update_tray(self):
        if not self.engine or not self.tray_icon:
            return

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
            self.tray_icon.title = f"FlowState ({status_text})\n{friendly}: {val}"

            menu_items = []
            menu_items.append(item(f"Status: {status_text}", lambda: None, enabled=False))
            menu_items.append(item("---", lambda: None, enabled=False))

            for i, v_name in enumerate(self.engine.settings_list):
                f_name = self.engine.setting_names[i]
                c_val = self.engine.settings[v_name]
                prefix = "▶ " if i == self.engine.current_setting_index else "  "
                menu_items.append(item(f"{prefix}{f_name}: {c_val}", lambda: None, enabled=False))

            menu_items.append(item("---", lambda: None, enabled=False))
            menu_items.append(item("Exit FlowState", self.exit_app))

            # Using self.tray_icon.menu assignment from a background thread can hang
            # if done too rapidly (like during countdown).
            if self.engine.countdown == 0 and not getattr(self, '_updating_menu', False):
                self._updating_menu = True
                self.tray_icon.menu = pystray.Menu(*menu_items)
                self._updating_menu = False

        except Exception as e:
            print(f"Tray Update Error: {e}")

    def exit_app(self):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        self.tray_icon.stop()
        sys.exit(0)

    def playwright_worker(self):
        try:
            with sync_playwright() as p:
                driver = PlaywrightDriverMac(p)
                self.engine = TypingEngine(driver)

                # Bind UI callbacks
                self.engine.ui_update_callback = self.update_tray
                self.engine.status_callback = self.update_tray
                self.update_tray()

                # ─── Register Hotkeys via pynput ───────────────────────────
                # pynput uses Key enums and KeyCode objects for hotkey combos.
                # On macOS: Key.cmd = ⌘, Key.alt = ⌥ (Option)

                def on_trigger():
                    if self.engine.is_running:
                        self.engine.set_state(paused=not self.engine.is_paused)
                    else:
                        # Capture the frontmost window title via AppleScript
                        window_title = PlaywrightDriverMac.get_frontmost_window_title()
                        self.pw_queue.put(("trigger_typing", window_title))

                def on_hud_cycle_up():
                    self.engine.cycle_hud(1)

                def on_hud_cycle_down():
                    self.engine.cycle_hud(-1)

                def on_hud_adjust_right():
                    self.engine.adjust_hud(1)

                def on_hud_adjust_left():
                    self.engine.adjust_hud(-1)

                def on_esc():
                    self.engine.handle_esc()

                # Define hotkey combinations using pynput's GlobalHotKeys
                # macOS: Cmd+Option+V to trigger, Cmd+Shift+Option+Arrows for HUD
                hotkeys = pynput_keyboard.GlobalHotKeys({
                    '<cmd>+<alt>+v': on_trigger,
                    '<cmd>+<alt>+<shift>+<up>': on_hud_cycle_up,
                    '<cmd>+<alt>+<shift>+<down>': on_hud_cycle_down,
                    '<cmd>+<alt>+<shift>+<right>': on_hud_adjust_right,
                    '<cmd>+<alt>+<shift>+<left>': on_hud_adjust_left,
                })
                hotkeys.start()
                self._hotkey_listener = hotkeys

                # Esc needs a separate listener since GlobalHotKeys doesn't
                # handle single-key presses well. We use a standard Listener.
                def on_press(key):
                    if key == pynput_keyboard.Key.esc:
                        on_esc()

                esc_listener = pynput_keyboard.Listener(on_press=on_press)
                esc_listener.daemon = True
                esc_listener.start()

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
