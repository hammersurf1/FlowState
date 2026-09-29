import os

from .playwright_driver import PlaywrightDriver


class PlaywrightDriverWin(PlaywrightDriver):
    def chrome_candidates(self):
        return [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
        ]

    def profile_dir(self):
        return r"C:\chrome-stealth-profile"
