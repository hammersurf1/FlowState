import sys

def get_driver():
    if sys.platform == "win32":
        from .win_driver import WinDriver
        return WinDriver()
    elif sys.platform == "darwin":
        from .mac_driver import MacDriver
        return MacDriver()
    elif sys.platform.startswith("linux"):
        raise NotImplementedError("Linux driver not yet implemented.")
    else:
        raise OSError("Unsupported Operating System")