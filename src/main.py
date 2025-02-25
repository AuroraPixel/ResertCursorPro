import os
import sys
import traceback

# 应用程序元数据
__version__ = '1.0.0'
__author__ = 'ResertCursorPro Team'

# 设置异常处理
def exception_handler(exctype, value, tb):
    error_msg = ''.join(traceback.format_exception(exctype, value, tb))
    print(f"未捕获的异常: {error_msg}")
    try:
        with open('error_log.txt', 'w') as f:
            f.write(f"未捕获的异常: {error_msg}")
    except:
        pass
    sys.__excepthook__(exctype, value, tb)

sys.excepthook = exception_handler

# 记录启动信息
print(f"应用程序启动，版本: {__version__}")
print(f"Python版本: {sys.version}")
print(f"运行模式: {'打包环境' if getattr(sys, 'frozen', False) else '开发环境'}")
print(f"工作目录: {os.getcwd()}")

# 设置 Qt 库路径（仅在开发环境需要）
if os.path.exists('/opt/homebrew/opt/qt/lib'):
    os.environ['DYLD_FRAMEWORK_PATH'] = '/opt/homebrew/opt/qt/lib'
    print("设置 Qt 库路径: /opt/homebrew/opt/qt/lib")

# 添加项目根目录到 Python 路径
if not getattr(sys, 'frozen', False):
    project_root = os.path.dirname(os.path.dirname(__file__))
    sys.path.insert(0, project_root)
    print(f"添加项目根目录到 Python 路径: {project_root}")

try:
    print("开始导入模块...")
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QIcon
    from src.views.login import LoginWindow
    from src.views.method import MethodWindow
    from src.components.logger import logger
    print("模块导入成功")
except Exception as e:
    print(f"模块导入失败: {str(e)}")
    traceback.print_exc()
    sys.exit(1)

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = os.path.abspath(".")
    
    full_path = os.path.join(base_path, relative_path)
    print(f"资源路径: {relative_path} -> {full_path}")
    return full_path

class Application:
    def __init__(self):
        try:
            print("初始化应用程序...")
            self.app = QApplication(sys.argv)
            self.app.setStyle("Fusion")
            print("设置应用程序样式: Fusion")
            
            # 设置应用程序图标
            icon_path = get_resource_path('resources/icon.ico')
            print(f"图标路径: {icon_path}")
            if os.path.exists(icon_path):
                print("图标文件存在")
                icon = QIcon(icon_path)
                self.app.setWindowIcon(icon)
            else:
                print("警告: 图标文件不存在")
            
            # 创建登录窗口
            print("创建登录窗口...")
            self.login_window = LoginWindow(self.on_login_success)
            self.method_window = None
            print("应用程序初始化完成")
        except Exception as e:
            print(f"应用程序初始化失败: {str(e)}")
            traceback.print_exc()
            raise
    
    def on_login_success(self):
        try:
            print("登录成功，创建主窗口...")
            # 创建并显示主方法窗口
            self.method_window = MethodWindow()
            self.method_window.show()
            print("主窗口显示成功")
        except Exception as e:
            print(f"创建主窗口失败: {str(e)}")
            traceback.print_exc()
    
    def run(self):
        try:
            print("显示登录窗口...")
            self.login_window.show()
            print("开始应用程序事件循环")
            return self.app.exec()
        except Exception as e:
            print(f"运行应用程序失败: {str(e)}")
            traceback.print_exc()
            return 1

def main():
    try:
        print("开始执行main函数")
        app = Application()
        exit_code = app.run()
        print(f"应用程序退出，退出码: {exit_code}")
        sys.exit(exit_code)
    except Exception as e:
        print(f"main函数执行失败: {str(e)}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    print("程序入口点执行")
    main() 