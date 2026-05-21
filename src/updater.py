"""
FlowState — Auto-Updater
Checks the GitHub Releases API for new versions on startup.
Downloads the new installer in the background, then notifies the UI
so the user can choose to update.

This is a "passive" updater:
  - Runs in a daemon thread (non-blocking)
  - Never interrupts the user
  - Adds a tray menu item when an update is ready
  - User clicks the menu item to launch the installer and exit
"""

import json
import os
import platform
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request

from version import __version__

GITHUB_REPO = "hammersurf1/FlowState"
RELEASES_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
REQUEST_TIMEOUT = 15  # seconds


class Updater:
    """
    Passive auto-updater that checks GitHub Releases in the background.

    Usage:
        updater = Updater(on_update_available=my_callback)
        updater.check_in_background()

    The callback receives (version_string, download_path) when an update
    has been downloaded and is ready to install.
    """

    def __init__(self, on_update_available=None):
        self.on_update_available = on_update_available
        self.update_available = False
        self.download_path = None
        self.latest_version = None

    def check_in_background(self):
        """Spawn a daemon thread that checks for updates without blocking startup."""
        thread = threading.Thread(target=self._check_and_download, daemon=True)
        thread.start()

    def _check_and_download(self):
        """Internal: query GitHub, compare versions, download if newer."""
        try:
            # 1. Query GitHub Releases API
            request = urllib.request.Request(
                RELEASES_URL,
                headers={
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": f"FlowState-Updater/{__version__}",
                },
            )
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                data = json.loads(response.read().decode("utf-8"))

            # 2. Compare versions
            tag = data.get("tag_name", "").lstrip("v")
            if not tag or not self._is_newer(tag, __version__):
                print(f"Updater: current v{__version__} is up to date.")
                return

            self.latest_version = tag
            print(f"Updater: new version v{tag} available (current: v{__version__}).")

            # 3. Find the correct asset for this platform
            asset_name = self._get_asset_name()
            asset_url = None
            for asset in data.get("assets", []):
                if asset.get("name") == asset_name:
                    asset_url = asset.get("browser_download_url")
                    break

            if not asset_url:
                print(f"Updater: no asset named '{asset_name}' in release v{tag}.")
                return

            # 4. Download to temp directory
            tmp_dir = os.path.join(tempfile.gettempdir(), "FlowState_Update")
            os.makedirs(tmp_dir, exist_ok=True)
            download_path = os.path.join(tmp_dir, asset_name)

            print(f"Updater: downloading {asset_name}...")
            urllib.request.urlretrieve(asset_url, download_path)
            print(f"Updater: download complete → {download_path}")

            self.download_path = download_path
            self.update_available = True

            # 5. Notify the UI
            if self.on_update_available:
                self.on_update_available(self.latest_version, self.download_path)

        except urllib.error.URLError as e:
            # Network errors are non-fatal — the user just doesn't get notified
            print(f"Updater: network error (non-fatal): {e}")
        except Exception as e:
            print(f"Updater: check failed (non-fatal): {e}")

    def launch_installer_and_exit(self):
        """Launch the downloaded installer and exit FlowState."""
        if not self.download_path or not os.path.exists(self.download_path):
            print("Updater: no downloaded installer to launch.")
            return

        print(f"Updater: launching installer {self.download_path}...")

        if sys.platform == "win32":
            os.startfile(self.download_path)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", self.download_path])
        else:
            subprocess.Popen(["xdg-open", self.download_path])

        sys.exit(0)

    @staticmethod
    def _is_newer(remote_version, local_version):
        """
        Compare two semver-style version strings.
        Returns True if remote_version > local_version.
        """
        try:
            def parse(v):
                return tuple(int(x) for x in v.split("."))
            return parse(remote_version) > parse(local_version)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def _get_asset_name():
        """Return the expected installer asset filename for this platform."""
        if sys.platform == "win32":
            return "FlowState_Windows_Setup.exe"
        elif sys.platform == "darwin":
            return "FlowState_Mac_Installer.dmg"
        else:
            return "FlowState_Linux.tar.gz"
