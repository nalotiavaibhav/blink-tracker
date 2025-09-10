# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('app_config.json', '.'), ('desktop', 'desktop'), ('shared', 'shared'), ('backend', 'backend')]
binaries = []
hiddenimports = ['desktop', 'desktop.main', 'desktop.eye_tracker', 'shared', 'shared.config', 'shared.api', 'shared.db', 'shared.google_oauth', 'backend', 'backend.models', 'backend.main', 'backend.emailer', 'cv2', 'mediapipe', 'psutil', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'requests', 'sqlite3', 'dotenv', 'pathlib', 'json', 'datetime', 'uuid', 'typing', 'dataclasses']
tmp_ret = collect_all('mediapipe')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['desktop\\main.py'],
    pathex=['.'],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'pytest', 'unittest'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='WellnessAtWork-Fixed',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['assets\\app.ico'],
)
