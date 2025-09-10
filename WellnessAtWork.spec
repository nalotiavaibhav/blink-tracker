# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas = [('assets', 'assets'), ('app_config.json', '.'), ('desktop', 'desktop'), ('shared', 'shared'), ('backend', 'backend')]
binaries = [('D:\\blink-tracker\\.venv\\Lib\\site-packages\\cryptography\\hazmat\\bindings\\_rust.pyd', '.')]
hiddenimports = ['cv2', 'mediapipe', 'psutil', 'PyQt6', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWidgets', 'requests', 'json', 'pathlib', 'datetime', 'uuid', 'dotenv', 'sqlite3', 'matplotlib', 'matplotlib.pyplot', 'numpy', 'sqlalchemy', 'sqlalchemy.ext', 'sqlalchemy.ext.declarative', 'sqlalchemy.orm', 'sqlalchemy.sql', 'sqlalchemy.engine', 'desktop.eye_tracker', 'shared.config', 'shared.api', 'shared.db', 'backend.models']
tmp_ret = collect_all('mediapipe')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('cv2')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('matplotlib')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]
tmp_ret = collect_all('sqlalchemy')
datas += tmp_ret[0]; binaries += tmp_ret[1]; hiddenimports += tmp_ret[2]


a = Analysis(
    ['desktop\\main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tests', 'pytest', 'unittest', 'tkinter'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='WellnessAtWork',
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
    icon=['assets\\app.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='WellnessAtWork',
)
