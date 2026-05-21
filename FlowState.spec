# -*- mode: python ; coding: utf-8 -*-
# FlowState Windows Build Spec (onedir mode)
from PyInstaller.utils.hooks import collect_all
import os

datas = [
    ('settings.ini.example', '.'),
    ('assets', 'assets'),
]
binaries = []
hiddenimports = ['settings_gui', 'first_run', 'updater', 'version']

# Collect playwright LIBRARY only — not the browser binaries.
# FlowState connects to the user's installed Chrome via CDP,
# so we don't need to ship a 200MB+ bundled Chromium.
tmp_ret = collect_all('playwright')
pw_datas = [(src, dst) for src, dst in tmp_ret[0]
            if not any(browser in src.lower()
                       for browser in ('chromium', 'firefox', 'webkit',
                                       'ffmpeg', 'chrome-', 'chrome_'))]
datas += pw_datas
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

a = Analysis(
    ['src\\main_win.py'],
    pathex=['src'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FlowState',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon=['assets\\icon.ico'],
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FlowState',
)
