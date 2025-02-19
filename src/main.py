import os
import sys

# 应用程序元数据
__version__ = '1.0.0'
__author__ = 'ResertCursorPro Team'

# 设置 Qt 库路径（仅在开发环境需要）
if os.path.exists('/opt/homebrew/opt/qt/lib'):
    os.environ['DYLD_FRAMEWORK_PATH'] = '/opt/homebrew/opt/qt/lib'

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QIcon
from views.login import LoginWindow
from views.method import MethodWindow

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        
        # 设置应用程序图标
        icon_path = get_resource_path('resources/icon.ico')
        icon = QIcon(icon_path)
        self.app.setWindowIcon(icon)
        
        # 创建登录窗口
        self.login_window = LoginWindow(self.on_login_success)
        self.method_window = None
    
    def on_login_success(self):
        # 创建并显示主方法窗口
        self.method_window = MethodWindow()
        self.method_window.show()
    
    def run(self):
        self.login_window.show()
        return self.app.exec()

def main():
    app = Application()
    sys.exit(app.run())

if __name__ == "__main__":
    main() 