"""
FlowState — Windows Entry Point
Launches the system tray app with the Playwright-based typing engine.
Uses the `keyboard` library for global hotkeys (requires Administrator on Windows).
"""

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
from os_layer.hybrid_driver_win import HybridDriver
from first_run import ensure_settings_file, ensure_chrome_profile_dir, check_chrome_installed, show_chrome_required_dialog
from updater import Updater
from version import __version__


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
        self.updater = Updater(on_update_available=self._on_update_available)
        self._pending_update_version = None

    def start(self):
        # First-run setup: ensure settings.ini exists
        ensure_settings_file()
        ensure_chrome_profile_dir()

        # Check that Chrome is installed (non-blocking warning if missing)
        if not check_chrome_installed():
            show_chrome_required_dialog()

        def setup_icon(icon):
            self.tray_icon.visible = True
            threading.Thread(target=self.playwright_worker, daemon=True).start()
            # Check for updates in the background (non-blocking)
            self.updater.check_in_background()

        # Setup System Tray (Must be on main thread)
        self.tray_icon = pystray.Icon("FlowState", create_image("#0078D7"), f"FlowState v{__version__}: Starting...")
        self.tray_icon.menu = pystray.Menu(item("Starting up...", lambda: None, enabled=False))

        print(f"FlowState v{__version__} starting... look for the system tray icon.")
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

            # Show update menu item if available
            if self._pending_update_version:
                menu_items.append(item(
                    f"⬆ Update to v{self._pending_update_version}",
                    self._do_update
                ))

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

    def re_register_hotkeys(self):
        """Unhook all keyboard hotkeys and re-register them with the current engine values."""
        try:
            keyboard.unhook_all_hotkeys()
        except Exception:
            pass

        trigger = self.engine.hotkeys.get("TriggerHotkey", "ctrl+alt+v")
        pause_key = self.engine.hotkeys.get("PauseKey", "esc")

        keyboard.add_hotkey(trigger, self._on_trigger)
        keyboard.add_hotkey('ctrl+alt+shift+up', lambda: self.engine.cycle_hud(1))
        keyboard.add_hotkey('ctrl+alt+shift+down', lambda: self.engine.cycle_hud(-1))
        keyboard.add_hotkey('ctrl+alt+shift+right', lambda: self.engine.adjust_hud(1))
        keyboard.add_hotkey('ctrl+alt+shift+left', lambda: self.engine.adjust_hud(-1))
        keyboard.add_hotkey(pause_key, self.engine.handle_esc)

    def _on_update_available(self, version, download_path):
        """Called by the Updater (from background thread) when a new version is ready."""
        print(f"Update available: v{version} → {download_path}")
        self._pending_update_version = version
        self.update_tray()  # Refresh menu to show update item

    def _do_update(self):
        """Launch the downloaded installer and exit."""
        self.updater.launch_installer_and_exit()

    def exit_app(self):
        self.tray_icon.stop()
        sys.exit(0)

    def playwright_worker(self):
        try:
            with sync_playwright() as p:
                driver = HybridDriver(p)
                self.engine = TypingEngine(driver)

                # Debug logging — set to True to write ~/.flowstate/debug.log
                self.engine.enable_debug(False)

                # Bind UI callbacks
                self.engine.ui_update_callback = self.update_tray
                self.engine.status_callback = self.update_tray
                self.update_tray()

                # Register Hotkeys — Windows uses the `keyboard` library
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
