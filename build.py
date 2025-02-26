import os
import platform
import subprocess
import shutil
import time
import sys
import argparse

def clean_build():
    """清理构建文件"""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"已清理 {dir_name} 目录")
            except PermissionError:
                print(f"警告: 无法删除 {dir_name} 目录，可能是权限问题或文件正在使用中")
                # 等待一会儿再试一次
                time.sleep(2)
                try:
                    shutil.rmtree(dir_name)
                    print(f"第二次尝试: 已清理 {dir_name} 目录")
                except Exception as e:
                    print(f"无法清理 {dir_name} 目录: {e}")

def build_macos():
    """构建 macOS 应用程序"""
    # 使用 spec 文件构建应用
    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--log-level=INFO',
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
        '--noconfirm',
        '--log-level=INFO',
        'ResertCursorPro.spec'
    ]
    subprocess.run(cmd, check=True)
    
    # 验证生成的可执行文件
    exe_path = 'dist/ResertCursorPro.exe'
    if os.path.exists(exe_path):
        print(f"成功创建Windows可执行文件: {exe_path}")
    else:
        print(f"错误: {exe_path} 未能成功创建")

def check_pyinstaller_wine():
    """检查是否安装了wine和pyinstaller-windows"""
    try:
        # 检查wine
        wine_result = subprocess.run(['which', 'wine'], capture_output=True, text=True)
        if wine_result.returncode != 0:
            print("错误: 未安装wine，无法在Mac上构建Windows应用")
            print("请安装wine: brew install --cask wine-stable")
            return False
        
        print("已检测到wine安装")
        return True
    except Exception as e:
        print(f"检查依赖时出错: {e}")
        return False

def build_windows_on_mac():
    """在Mac上构建Windows应用程序"""
    if not check_pyinstaller_wine():
        return False
    
    # 备份原始spec文件
    shutil.copy('ResertCursorPro.spec', 'ResertCursorPro.spec.bak')
    
    try:
        print("在Mac上构建Windows应用程序...")
        
        # 修改spec文件以强制Windows目标
        with open('ResertCursorPro.spec', 'r') as f:
            content = f.read()
        
        # 替换icon设置
        content = content.replace(
            "icon=['resources/icon.ico', 'resources/icon.icns'] if sys.platform == 'darwin' else 'resources/icon.ico'",
            "icon='resources/icon.ico'"
        )
        
        # 暂时移除Mac特定的BUNDLE部分
        if_darwin_index = content.find("if sys.platform == 'darwin':")
        if if_darwin_index > 0:
            content = content[:if_darwin_index]
        
        with open('ResertCursorPro.spec', 'w') as f:
            f.write(content)
        
        # 使用wine和pyinstaller构建Windows应用
        cmd = [
            'wine',
            'python',
            '-m',
            'PyInstaller',
            '--noconfirm',
            '--log-level=INFO',
            'ResertCursorPro.spec'
        ]
        
        print("开始使用Wine构建Windows应用...")
        print("运行命令: " + " ".join(cmd))
        
        result = subprocess.run(cmd, check=False)
        
        if result.returncode == 0:
            print("成功在Mac上构建Windows应用")
            return True
        else:
            print(f"构建失败，返回代码: {result.returncode}")
            return False
            
    except Exception as e:
        print(f"在Mac上构建Windows应用时出错: {e}")
        return False
    finally:
        # 恢复原始spec文件
        if os.path.exists('ResertCursorPro.spec.bak'):
            shutil.move('ResertCursorPro.spec.bak', 'ResertCursorPro.spec')

def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='构建ResertCursorPro应用程序')
    parser.add_argument('--target', choices=['auto', 'macos', 'windows'], default='auto',
                        help='指定构建目标平台 (默认: auto)')
    args = parser.parse_args()
    
    # 检查资源文件
    if not os.path.exists('resources/icon.icns'):
        print("错误: 图标文件 'resources/icon.icns' 不存在！")
        return
    
    if not os.path.exists('resources/icon.ico'):
        print("错误: 图标文件 'resources/icon.ico' 不存在！")
        return
    
    if not os.path.exists('src/turnstilePatch'):
        print("错误: turnstilePatch 目录不存在！")
        return
    
    # 尝试清理旧的构建文件
    print("开始清理旧的构建文件...")
    clean_build()
    
    # 获取当前系统
    current_system = platform.system()
    print(f"当前操作系统: {current_system}")
    
    # 确定构建目标
    target_platform = args.target
    if target_platform == 'auto':
        target_platform = 'macos' if current_system == 'Darwin' else 'windows'
    
    print(f"目标构建平台: {target_platform}")
    print("开始构建全量独立应用程序...")
    
    # 根据目标平台选择构建方法
    if target_platform == 'macos':
        if current_system == 'Darwin':
            build_macos()
            print("构建完成！")
            print("可执行文件位于: dist/ResertCursorPro.app")
            print("DMG 文件位于: dist/ResertCursorPro.dmg")
        else:
            print("错误: 无法在非Mac系统上构建Mac应用")
    elif target_platform == 'windows':
        if current_system == 'Windows':
            build_windows()
            print("构建完成！")
            print("可执行文件位于: dist/ResertCursorPro.exe")
        else:
            # 在Mac上尝试构建Windows应用
            if current_system == 'Darwin':
                success = build_windows_on_mac()
                if success:
                    print("构建完成！")
                    print("Windows可执行文件位于: dist/ResertCursorPro.exe")
                else:
                    print("在Mac上构建Windows应用失败")
                    print("请考虑使用Windows虚拟机或使用Docker容器来构建Windows应用")
            else:
                print(f"错误: 在{current_system}上构建Windows应用的功能尚未实现")

if __name__ == '__main__':
    main() 