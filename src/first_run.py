"""
FlowState — First-Run Setup
Handles initial setup tasks on the first launch:
  1. Creates settings.ini from the bundled template if missing.
  2. Checks that Google Chrome is installed (required for CDP typing).
"""

import os
import sys
import shutil
import platform


def _get_app_dir():
    """Return the directory where the running executable (or script) lives."""
    if getattr(sys, 'frozen', False):
        # Running as a PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Running as a script
        return os.path.dirname(os.path.abspath(__file__))


def ensure_settings_file():
    """
    If settings.ini doesn't exist next to the executable, create one
    from settings.ini.example (bundled by PyInstaller).
    """
    app_dir = _get_app_dir()
    settings_path = os.path.join(app_dir, "settings.ini")
    template_path = os.path.join(app_dir, "settings.ini.example")

    if os.path.exists(settings_path):
        return  # Already set up

    if os.path.exists(template_path):
        shutil.copy2(template_path, settings_path)
        print(f"Created settings.ini from template.")
    else:
        # Fallback: create a minimal settings.ini
        with open(settings_path, "w") as f:
            f.write("[Settings]\n")
            f.write("usermeandelay = 110\n")
            f.write("uservariance = 45\n")
            f.write("typochance = 7\n")
            f.write("typodelay = 100\n")
            f.write("revisionchance = 3\n")
        print("Created minimal settings.ini (template not found).")


def _get_chrome_paths():
    """Return a list of known Chrome installation paths for the current OS."""
    system = platform.system()

    if system == "Windows":
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        return [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(local_app_data, r"Google\Chrome\Application\chrome.exe"),
        ]
    elif system == "Darwin":
        return [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
    else:
        return [
            "/usr/bin/google-chrome",
            "/usr/bin/google-chrome-stable",
            "/usr/bin/chromium-browser",
            "/usr/bin/chromium",
        ]


def check_chrome_installed():
    """
    Check if Google Chrome is installed at any known path.
    Returns True if Chrome is found, False otherwise.
    """
    for path in _get_chrome_paths():
        if os.path.exists(path):
            return True
    return False


def ensure_chrome_profile_dir():
    """Create the dedicated Chrome profile directory used by the
    FlowState Chrome shortcut launcher."""
    system = platform.system()
    if system == "Windows":
        profile_dir = os.path.join(
            os.environ.get("LOCALAPPDATA", ""), "FlowState", "ChromeProfile"
        )
    elif system == "Darwin":
        profile_dir = os.path.join(
            os.path.expanduser("~"),
            "Library",
            "Application Support",
            "FlowState",
            "ChromeProfile",
        )
    else:
        return
    os.makedirs(profile_dir, exist_ok=True)


def show_chrome_required_dialog():
    """
    Show a user-friendly dialog explaining that Chrome is required.
    Uses tkinter (bundled with Python) — no extra dependencies.
    The dialog is non-blocking: the user can dismiss it and the app
    will continue to run (Chrome might be installed in a non-standard path).
    """
    try:
        import tkinter as tk
        from tkinter import messagebox

        # Create a hidden root window (messagebox needs one)
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        system = platform.system()
        if system == "Darwin":
            hotkey = "⌘+⌥+V"
            chrome_name = "Google Chrome"
            download_note = (
                "Download Chrome from:\n"
                "https://www.google.com/chrome\n\n"
                "After installing Chrome, restart FlowState."
            )
        else:
            hotkey = "Ctrl+Alt+V"
            download_note = (
                "Download Chrome from:\n"
                "https://www.google.com/chrome\n\n"
                "After installing Chrome, restart FlowState."
            )

        messagebox.showwarning(
            "FlowState — Chrome Required for Browser Mode",
            f"FlowState works in TWO modes:\n\n"
            f"  1. Browser Mode (Playwright)\n"
            f"     Types into {chrome_name} tabs via the debug port.\n"
            f"     Open Chrome with the 'FlowState Chrome' shortcut first,\n"
            f"     then press {hotkey} in that Chrome window.\n\n"
            f"  2. OS Mode\n"
            f"     Types into ANY app using OS-level keystrokes.\n"
            f"     Just press {hotkey} in any window — no Chrome needed.\n\n"
            f"{download_note}"
        )

        root.destroy()

    except Exception as e:
        # If tkinter is unavailable, fall back to a console message
        print("=" * 50)
        print("  FlowState — Chrome Required for Browser Mode")
        print("=" * 50)
        print()
        print("  FlowState works in two modes:")
        print("    1. Browser Mode — types into Chrome via debug port")
        print("    2. OS Mode      — types into any app with OS keystrokes")
        print()
        print("  Download Chrome from: https://www.google.com/chrome")
        print()
        print(f"  (tkinter dialog failed: {e})")
        print("=" * 50)
