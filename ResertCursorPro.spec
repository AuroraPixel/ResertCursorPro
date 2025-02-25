# -*- mode: python ; coding: utf-8 -*-

import sys

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('resources', 'resources'),
        ('src/turnstilePatch', 'turnstilePatch')
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
        'PyQt6.sip',
        'src.views.login',
        'src.views.method',
        'src.components.logger',
        'src.components.reset_machine',
        'src.components.exit_cursor',
        'src.components.account_switcher',
        'src.components.register_account',
        'src.components.account_service',
        'src.views.account_dialog',
        'src.components.cursor_auth_manager',
        'src.components.get_email_code_temp',
        'src.components.browser_utils',
        'src.config',
        'colorama',
        'psutil',
        'requests',
        'PyJWT',
        'DrissionPage',
        'dotenv'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ResertCursorPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['resources/icon.ico', 'resources/icon.icns'] if sys.platform == 'darwin' else 'resources/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ResertCursorPro',
)

app = BUNDLE(
    coll,
    name='ResertCursorPro.app',
    icon='resources/icon.icns' if sys.platform == 'darwin' else 'resources/icon.ico',
    bundle_identifier='com.resertcursorpro.app',
    info_plist={
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'NSHighResolutionCapable': 'True',
        'LSMinimumSystemVersion': '10.13.0',
        'NSPrincipalClass': 'NSApplication',
        'NSAppleScriptEnabled': False,
    },
)
