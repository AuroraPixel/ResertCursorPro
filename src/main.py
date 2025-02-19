import os
import sys

# 应用程序元数据
__version__ = '1.0.0'
__author__ = 'ResertCursorPro Team'

# 设置 Qt 库路径（仅在开发环境需要）
if os.path.exists('/opt/homebrew/opt/qt/lib'):
    os.environ['DYLD_FRAMEWORK_PATH'] = '/opt/homebrew/opt/qt/lib'

from PyQt6.QtWidgets import QApplication
from views.login import LoginWindow
from views.method import MethodWindow

class Application:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setStyle("Fusion")
        
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