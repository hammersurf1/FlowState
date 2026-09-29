import os
import subprocess

from .playwright_driver import PlaywrightDriver


class PlaywrightDriverMac(PlaywrightDriver):
    def chrome_candidates(self):
        return ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"]

    def profile_dir(self):
        return os.path.expanduser("~/Library/Application Support/FlowState/chrome-debug-profile")

    def detect_layout(self):
        """Detect keyboard layout on macOS via system defaults."""
        try:
            result = subprocess.run(
                ["defaults", "read", "-g", "AppleCurrentKeyboardLayoutInputSourceID"],
                capture_output=True, text=True, timeout=5
            )
            layout_id = result.stdout.strip().lower()
            if "german" in layout_id or "qwertz" in layout_id:
                return "QWERTZ"
            if "french" in layout_id or "azerty" in layout_id:
                return "AZERTY"
        except Exception:
            pass
        return "QWERTY"

    @staticmethod
    def get_frontmost_window_title():
        """Use AppleScript to get the title of the frontmost window (for tab matching)."""
        try:
            result = subprocess.run(
                ["osascript", "-e",
                 'tell application "System Events" to get name of first window '
                 'of (first application process whose frontmost is true)'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""
