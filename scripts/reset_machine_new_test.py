import os
import sys

# 获取项目的根路径，并将其添加到系统路径，以便成功导入模块
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# 导入已转换的功能模块
import src.components.reset_machine_new as rm

def update_main_js():
    # 假设 update_main_js_content 是一个异步函数
    file_path = r"C:\Users\w\AppData\Local\Programs\cursor\resources\app\out\main.js"
    rm.update_main_js_content(file_path)

def main():
    update_main_js()

if __name__ == "__main__":
    main()