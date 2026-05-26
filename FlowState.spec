# -*- mode: python ; coding: utf-8 -*-
# FlowState Windows Build Spec (onedir mode)
from PyInstaller.utils.hooks import collect_all
import os

datas = [
    ('settings.ini.example', '.'),
    ('assets', 'assets'),
    ('scripts/launch_chrome_win.bat', '.'),
]
binaries = []
hiddenimports = ['settings_gui', 'first_run', 'updater', 'version', 'os_layer.os_typing_driver_win', 'os_layer.hybrid_driver_win', 'os_layer.playwright_driver_win', 'os_layer.playwright_driver_mac', 'rich_text_formatter', 'semantic_analyzer', 'typing_planner', 'formatters', 'formatters.google_docs_formatter', 'formatters.instruction', 'formatters.backends.cdp_backend', 'formatters.backends.os_backend']

# Collect playwright LIBRARY only — not the browser binaries.
tmp_ret = collect_all('playwright')
pw_datas = [(src, dst) for src, dst in tmp_ret[0]
            if not any(browser in src.lower()
                       for browser in ('chromium', 'firefox', 'webkit',
                                       'ffmpeg', 'chrome-', 'chrome_'))]
datas += pw_datas
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# Bundle spaCy + model so the installer is fully self-contained
for pkg in ('spacy', 'thinc', 'blis', 'en_core_web_md'):
    try:
        pkg_ret = collect_all(pkg)
        datas += pkg_ret[0]
        binaries += pkg_ret[1]
        hiddenimports += pkg_ret[2]
    except Exception:
        pass

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
