import os
import platform
import subprocess
import shutil
import sys

def clean_build():
    """清理构建文件"""
    dirs_to_clean = ['build', 'dist', 'obfuscated']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

def build_secure():
    """构建加密版本"""
    try:
        print("开始构建加密版本...")
        
        # 检查必要文件和目录
        if not os.path.exists('src/turnstilePatch'):
            print("错误: turnstilePatch 目录不存在！")
            return
        
        # 1. 清理旧的构建文件
        print("1. 清理旧的构建文件...")
        clean_build()
        
        # 2. 使用PyArmor加密源代码
        print("2. 使用PyArmor加密源代码...")
        
        # 检查Python版本
        if sys.version_info >= (3, 11):
            print("警告: 当前Python版本不支持PyArmor，跳过加密步骤...")
        else:
            os.makedirs('obfuscated', exist_ok=True)
            subprocess.run([
                'pyarmor', 'obfuscate',
                '--recursive',
                '--output', 'obfuscated',
                'src/main.py'
            ], check=True)
        
        # 3. 使用PyInstaller构建程序
        print("3. 使用PyInstaller构建程序...")
        
        # 基本构建命令
        build_cmd = [
            'pyinstaller',
            '--clean',
            '--noconfirm'
        ]
        
        # 添加资源文件
        if platform.system() == 'Darwin':
            build_cmd.extend(['--add-data', 'src/turnstilePatch:turnstilePatch'])
        else:
            build_cmd.extend(['--add-data', 'src/turnstilePatch;turnstilePatch'])
            
        build_cmd.append('secure.spec')
        
        # 执行构建
        subprocess.run(build_cmd, check=True)
        
        print("构建完成！")
        
        # 输出构建结果位置
        if platform.system() == 'Darwin':
            print("可执行文件位于: dist/ResertCursorPro.app")
        elif platform.system() == 'Windows':
            print("可执行文件位于: dist/ResertCursorPro/ResertCursorPro.exe")
        
    except subprocess.CalledProcessError as e:
        print(f"构建失败: {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"发生错误: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    build_secure() 