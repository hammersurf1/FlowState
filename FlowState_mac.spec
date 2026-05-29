# -*- mode: python ; coding: utf-8 -*-
# FlowState macOS Build Spec (app bundle)
from PyInstaller.utils.hooks import collect_all
import os

datas = [
    ('settings.ini.example', '.'),
    ('assets', 'assets'),
]
binaries = []
hiddenimports = ['settings_gui', 'first_run', 'updater', 'version', 'iki_timing']

# Collect playwright LIBRARY only — not the browser binaries.
tmp_ret = collect_all('playwright')
pw_datas = [(src, dst) for src, dst in tmp_ret[0]
            if not any(browser in src.lower()
                       for browser in ('chromium', 'firefox', 'webkit',
                                       'ffmpeg', 'chrome-', 'chrome_'))]
datas += pw_datas
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# CustomTkinter theme assets
for pkg in ('customtkinter', 'darkdetect'):
    try:
        pkg_ret = collect_all(pkg)
        datas += pkg_ret[0]
        binaries += pkg_ret[1]
        hiddenimports += pkg_ret[2]
    except Exception:
        pass

# Bundle spaCy + model so the installer is fully self-contained
for pkg in ('spacy', 'thinc', 'blis', 'en_core_web_md', 'nltk'):
    try:
        pkg_ret = collect_all(pkg)
        datas += pkg_ret[0]
        binaries += pkg_ret[1]
        hiddenimports += pkg_ret[2]
    except Exception:
        pass

a = Analysis(
    ['src/main_mac.py'],
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
    icon=['assets/logo.icns'],
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

app = BUNDLE(
    coll,
    name='FlowState.app',
    icon='assets/logo.icns',
    bundle_identifier='com.hammersurf.flowstate',
)
