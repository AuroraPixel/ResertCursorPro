import os
import platform
import subprocess
import shutil

def clean_build():
    """清理构建文件"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

def build_macos():
    """构建 macOS 应用程序"""
    # 使用 spec 文件构建应用
    cmd = [
        'pyinstaller',
        # '--clean',  # 移除清理参数
        '--noconfirm',
        '--log-level=DEBUG',
        'ResertCursorPro.spec'
    ]
    subprocess.run(cmd, check=True)
    
    # 检查 .app 文件是否存在
    app_path = 'dist/ResertCursorPro.app'
    if not os.path.exists(app_path):
        print(f"错误: {app_path} 未能成功创建")
        return
    
    # 创建 DMG
    dmg_path = 'dist/ResertCursorPro.dmg'
    if os.path.exists(dmg_path):
        os.remove(dmg_path)
    
    try:
        subprocess.run([
            'hdiutil', 'create',
            '-volname', 'ResertCursorPro',
            '-srcfolder', app_path,
            '-ov', dmg_path,
            '-format', 'UDZO'
        ], check=True)
        print(f"成功创建 DMG 文件: {dmg_path}")
    except subprocess.CalledProcessError as e:
        print(f"创建 DMG 文件失败: {e}")

def build_windows():
    """构建 Windows 应用程序"""
    cmd = [
        'pyinstaller',
        # '--clean',  # 移除清理参数
        '--noconfirm',
        '--log-level=DEBUG',
        'ResertCursorPro.spec'
    ]
    subprocess.run(cmd, check=True)

def main():
    # 检查资源文件
    if not os.path.exists('resources/icon.icns'):
        print("错误: 图标文件 'resources/icon.icns' 不存在！")
        return
    
    if not os.path.exists('src/turnstilePatch'):
        print("错误: turnstilePatch 目录不存在！")
        return
    
    # 清理旧的构建文件
    # clean_build()  # 注释掉清理步骤，避免权限问题
    print("跳过清理步骤，直接开始构建...")
    
    # 根据操作系统选择构建方法
    system = platform.system()
    if system == 'Darwin':
        build_macos()
    elif system == 'Windows':
        build_windows()
    else:
        print(f"不支持的操作系统: {system}")
        return

    print("构建完成！")
    if system == 'Darwin':
        print("可执行文件位于: dist/ResertCursorPro.app")
        print("DMG 文件位于: dist/ResertCursorPro.dmg")
    elif system == 'Windows':
        print("可执行文件位于: dist/ResertCursorPro/ResertCursorPro.exe")

if __name__ == '__main__':
    main() 