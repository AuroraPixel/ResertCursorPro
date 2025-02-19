# -*- mode: python ; coding: utf-8 -*-

import sys
import platform
from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT, BUNDLE

# 使用自定义加密密钥
block_cipher = None

# 根据平台设置图标
if platform.system() == 'Darwin':
    icon_file = 'resources/icon.icns'
else:
    icon_file = 'resources/icon.ico'

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[('resources', 'resources')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=True,  # 禁用优化以增加保护
)

# 添加额外的混淆选项
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

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
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=True,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_file,
    version='file_version_info.txt' if platform.system() == 'Windows' else None,
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

if platform.system() == 'Darwin':
    app = BUNDLE(
        coll,
        name='ResertCursorPro.app',
        icon=icon_file,
        bundle_identifier='com.resertcursorpro.app',
        info_plist={
            'CFBundleShortVersionString': '1.0.0',
            'CFBundleVersion': '1.0.0',
            'NSHighResolutionCapable': 'True',
            'LSMinimumSystemVersion': '10.13.0',
            'NSPrincipalClass': 'NSApplication',
            'NSAppleScriptEnabled': False,
            'CFBundleDisplayName': 'ResertCursorPro',
            'CFBundleName': 'ResertCursorPro',
            'CFBundlePackageType': 'APPL',
            'CFBundleSignature': '????',
            'LSApplicationCategoryType': 'public.app-category.utilities',
        },
    )
