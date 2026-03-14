# -*- mode: python ; coding: utf-8 -*-
# PyInstaller build spec for MicProject Installer
# Build: python -m PyInstaller installer.spec --noconfirm --clean

block_cipher = None

a = Analysis(
    ['installer.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('../pc-server/assets', 'assets'),  # Include icon
        ('bundled', 'bundled'),              # Include MicProject.exe
    ],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=['numpy', 'scipy', 'matplotlib', 'pandas'],
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
    name='MicProjectSetup',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,        # No console for installer — GUI only
    icon='../pc-server/assets/icon.ico',
    uac_admin=False,      # Will request admin only for VB-Cable if needed
)
