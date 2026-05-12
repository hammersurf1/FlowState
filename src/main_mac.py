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
        self._esc_listener = None

    def start(self):
        def setup_icon(icon):
            self.tray_icon.visible = True
            threading.Thread(target=self.playwright_worker, daemon=True).start()

        # Setup System Tray (Must be on main thread for macOS)
        self.tray_icon = pystray.Icon("FlowState", create_image("#0078D7"), "FlowState: Starting...")
        self.tray_icon.menu = pystray.Menu(item("Starting up...", lambda: None, enabled=False))

        print("FlowState starting... look for the menu bar icon.")
        self.tray_icon.run(setup=setup_icon)

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
            menu_items.append(item("⚙ Settings...", self.open_settings))
            menu_items.append(item("Exit FlowState", self.exit_app))

            # Using self.tray_icon.menu assignment from a background thread can hang
            # if done too rapidly (like during countdown).
            if self.engine.countdown == 0 and not getattr(self, '_updating_menu', False):
                self._updating_menu = True
                self.tray_icon.menu = pystray.Menu(*menu_items)
                self._updating_menu = False

        except Exception as e:
            print(f"Tray Update Error: {e}")

    def open_settings(self):
        """Launch the Settings GUI in a separate thread (tkinter needs its own mainloop)."""
        threading.Thread(target=self._run_settings_gui, daemon=True).start()

    def _run_settings_gui(self):
        from settings_gui import SettingsWindow
        SettingsWindow(self.engine, on_hotkey_change=self.re_register_hotkeys)

    def _on_trigger(self):
        """Handle the typing trigger hotkey press."""
        if self.engine.is_running:
            self.engine.set_state(paused=not self.engine.is_paused)
        else:
            # Capture the frontmost window title via AppleScript
            window_title = PlaywrightDriverMac.get_frontmost_window_title()
            self.pw_queue.put(("trigger_typing", window_title))

    def re_register_hotkeys(self):
        """Stop the existing hotkey listener and start a new one with updated key combos."""
        # Stop existing listeners
        if self._hotkey_listener:
            self._hotkey_listener.stop()
            self._hotkey_listener = None
        if self._esc_listener:
            self._esc_listener.stop()
            self._esc_listener = None

        trigger = self.engine.hotkeys.get("TriggerHotkey", "cmd+alt+v")
        pause_key = self.engine.hotkeys.get("PauseKey", "esc")

        # Convert our key format to pynput format: ctrl+alt+v -> <ctrl>+<alt>+v
        def to_pynput_combo(combo_str):
            parts = combo_str.lower().split("+")
            converted = []
            for part in parts:
                part = part.strip()
                if part in ("ctrl", "cmd", "alt", "shift",
                            "up", "down", "left", "right"):
                    converted.append(f"<{part}>")
                else:
                    converted.append(part)
            return "+".join(converted)

        # Build hotkey dict
        hotkey_dict = {
            to_pynput_combo(trigger): self._on_trigger,
            '<cmd>+<alt>+<shift>+<up>': lambda: self.engine.cycle_hud(1),
            '<cmd>+<alt>+<shift>+<down>': lambda: self.engine.cycle_hud(-1),
            '<cmd>+<alt>+<shift>+<right>': lambda: self.engine.adjust_hud(1),
            '<cmd>+<alt>+<shift>+<left>': lambda: self.engine.adjust_hud(-1),
        }

        hotkeys = pynput_keyboard.GlobalHotKeys(hotkey_dict)
        hotkeys.start()
        self._hotkey_listener = hotkeys

        # Esc / pause key listener
        resolved_pause = pause_key.lower()
        def on_press(key):
            if resolved_pause == "esc" and key == pynput_keyboard.Key.esc:
                self.engine.handle_esc()

        esc_listener = pynput_keyboard.Listener(on_press=on_press)
        esc_listener.daemon = True
        esc_listener.start()
        self._esc_listener = esc_listener

    def exit_app(self):
        if self._hotkey_listener:
            self._hotkey_listener.stop()
        if self._esc_listener:
            self._esc_listener.stop()
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
                # Use engine.hotkeys for configurable key combos
                self.re_register_hotkeys()

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
