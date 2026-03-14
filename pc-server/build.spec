# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for MicProject PC Server
# Build: python -m PyInstaller build.spec

import sys
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('assets', 'assets')],
    hiddenimports=[
        'pystray._win32',
        'sounddevice',
        'numpy',
        'pynput.keyboard._win32',
        'pynput.mouse._win32',
        '_sounddevice_data',
        'i18n',
        'dashboard',
        'version',
        'updater',
        'psutil',
        'PIL',
        'PIL.Image',
        'PIL.ImageDraw',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'unittest',
        'pydoc',
        'doctest',
        'test',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='MicProject',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX DISABLED - avoids antivirus false positives
    console=False,        # No CMD window — GUI only
    icon='assets/icon.ico', # Added custom icon
    uac_admin=False,      # No admin rights needed
)
