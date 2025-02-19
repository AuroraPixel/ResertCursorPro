import os
import sys
import shutil
import subprocess
import platform
from datetime import datetime

def clean_build():
    """清理构建文件"""
    dirs_to_clean = ['build', 'dist', '__pycache__']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
    
    # 清理.pyc文件
    for root, dirs, files in os.walk('.'):
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))

def encrypt_with_pyarmor():
    """使用PyArmor加密源代码"""
    # 创建加密配置
    cmd = [
        'pyarmor-7', 'obfuscate',
        '--recursive',
        '--restrict=0',
        '--advanced', '2',
        '--platform', 'windows.x86_64' if platform.system() == 'Windows' else 'darwin.x86_64',
        'src/main.py'
    ]
    subprocess.run(cmd, check=True)

def build_with_pyinstaller():
    """使用PyInstaller构建程序"""
    # 运行PyInstaller
    cmd = [
        'pyinstaller',
        '--clean',
        '--noconfirm',
        'secure.spec'
    ]
    
    # 在Mac上添加额外的参数
    if platform.system() == 'Darwin':
        cmd.extend([
            '--windowed',  # 确保在Mac上创建.app包
            '--osx-bundle-identifier=com.resertcursorpro.app'
        ])
    
    subprocess.run(cmd, check=True)

def create_dmg():
    """在Mac上创建DMG安装包"""
    if platform.system() != 'Darwin':
        return
    
    try:
        # 创建DMG
        subprocess.run([
            'hdiutil',
            'create',
            '-volname', 'ResertCursorPro',
            '-srcfolder', 'dist/ResertCursorPro.app',
            '-ov',
            '-format', 'UDZO',
            'dist/ResertCursorPro.dmg'
        ], check=True)
        print("DMG文件创建成功：dist/ResertCursorPro.dmg")
    except Exception as e:
        print(f"创建DMG文件失败: {str(e)}")

def main():
    try:
        print("开始构建加密版本...")
        print("1. 清理旧的构建文件...")
        clean_build()
        
        print("2. 使用PyArmor加密源代码...")
        encrypt_with_pyarmor()
        
        print("3. 使用PyInstaller构建程序...")
        build_with_pyinstaller()
        
        # 在Mac上创建DMG
        if platform.system() == 'Darwin':
            print("4. 创建DMG安装包...")
            create_dmg()
        
        print("\n构建完成！")
        if platform.system() == 'Windows':
            print("可执行文件位于: dist/ResertCursorPro/ResertCursorPro.exe")
        else:
            print("应用程序位于: dist/ResertCursorPro.app")
            print("DMG安装包位于: dist/ResertCursorPro.dmg")
            
    except Exception as e:
        print(f"构建失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 