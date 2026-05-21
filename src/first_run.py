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
            "FlowState — Chrome Required",
            f"FlowState needs Google Chrome to work.\n\n"
            f"FlowState types into Chrome browser tabs by connecting to\n"
            f"Chrome's debugging interface. When you press {hotkey},\n"
            f"FlowState will simulate typing in the active Chrome tab.\n\n"
            f"{download_note}"
        )

        root.destroy()

    except Exception as e:
        # If tkinter is unavailable, fall back to a console message
        print("=" * 50)
        print("  FlowState — Chrome Required")
        print("=" * 50)
        print()
        print("  FlowState needs Google Chrome to work.")
        print("  Download from: https://www.google.com/chrome")
        print()
        print(f"  (tkinter dialog failed: {e})")
        print("=" * 50)
