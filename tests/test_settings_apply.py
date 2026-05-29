"""Settings apply/persist logic (no GUI)."""

import configparser
from pathlib import Path
from unittest.mock import MagicMock

import settings_gui as sg


def test_gather_and_timing_keys():
    import tkinter as tk

    root = tk.Tk()
    root.withdraw()
    try:
        win = object.__new__(sg.SettingsWindow)
        win.vars = {
            "UserMeanDelay": tk.IntVar(master=root, value=42),
            "EnableTypos": tk.BooleanVar(master=root, value=True),
        }
        win.hotkey_recorders = {
            "TriggerHotkey": MagicMock(value="ctrl+alt+v"),
            "PauseKey": MagicMock(value="esc"),
        }
        win.engine = MagicMock()
        win.engine.hotkeys = {"TriggerHotkey": "ctrl+alt+v", "PauseKey": "esc"}

        settings, hotkeys, changed = win._gather_settings_from_ui()
        assert settings["UserMeanDelay"] == 42
        assert settings["EnableTypos"] == 1
        assert hotkeys["TriggerHotkey"] == "ctrl+alt+v"
        assert changed is False
    finally:
        root.destroy()


def test_preview_timing_scale():
    base = {"UserMeanDelay": 100, "TypoChance": 5, "SentencePauseMs": 2000}
    speed = 2.0
    preview = {}
    for k, v in base.items():
        if sg._is_timing_setting_key(k, v):
            preview[k] = max(1, int(v / speed))
        else:
            preview[k] = v
    assert preview["UserMeanDelay"] == 50
    assert preview["SentencePauseMs"] == 1000
    assert preview["TypoChance"] == 5


def test_first_run_uses_flowstate_home(tmp_path, monkeypatch):
    from first_run import ensure_settings_file

    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", lambda: home)

    ensure_settings_file()
    ini = home / ".flowstate" / "settings.ini"
    assert ini.exists()
