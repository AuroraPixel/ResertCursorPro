import logging
import os
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

# 添加一个全局的日志回调函数
ui_log_callback = None

def set_ui_log_callback(callback):
    """设置UI日志回调函数"""
    global ui_log_callback
    ui_log_callback = callback

class UILogHandler(logging.Handler):
    """将日志发送到UI界面的处理器"""
    def emit(self, record):
        global ui_log_callback
        if ui_log_callback:
            log_entry = self.format(record)
            ui_log_callback(log_entry)

def setup_logger(name='ResertCursorPro'):
    """
    配置日志记录器
    
    Args:
        name: 日志记录器名称
    
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志记录器
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 清除所有已存在的处理器
    logger.handlers.clear()
    
    # 防止日志重复
    logger.propagate = False
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 创建UI日志处理器
    ui_handler = UILogHandler()
    ui_handler.setLevel(logging.INFO)
    ui_handler.setFormatter(formatter)
    logger.addHandler(ui_handler)
    
    # 如果在打包环境中，添加文件处理器
    if getattr(sys, 'frozen', False):
        try:
            # 获取应用程序所在目录
            if sys.platform == 'darwin':  # macOS
                app_dir = os.path.dirname(os.path.dirname(os.path.dirname(sys.executable)))
            else:  # Windows 和 Linux
                app_dir = os.path.dirname(sys.executable)
            
            # 创建日志目录
            log_dir = os.path.join(app_dir, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            # 创建日志文件名（使用当前日期）
            log_file = os.path.join(log_dir, f'resertcursor_{datetime.now().strftime("%Y%m%d")}.log')
            
            # 创建文件处理器（限制单个文件大小为 5MB，最多保留 5 个文件）
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=5*1024*1024,  # 5MB
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
            logger.info(f"日志文件位置: {log_file}")
            
        except Exception as e:
            logger.error(f"设置文件日志失败: {str(e)}")
    
    return logger

# 创建全局日志记录器实例
logger = setup_logger()

def main_task():
    """
    Main task execution function. Simulates a workflow and handles errors.
    """
    try:
        logging.info("Starting the main task...")

        # Simulated task and error condition
        if some_condition():
            raise ValueError("Simulated error occurred.")

        logging.info("Main task completed successfully.")

    except ValueError as ve:
        logging.error(f"ValueError occurred: {ve}", exc_info=True)
    except Exception as e:
        logging.error(f"Unexpected error occurred: {e}", exc_info=True)
    finally:
        logging.info("Task execution finished.")


def some_condition():
    """
    Simulates an error condition. Returns True to trigger an error.
    Replace this logic with actual task conditions.
    """
    return True


if __name__ == "__main__":
    # Application workflow
    logging.info("Application started.")
    main_task()
    logging.info("Application exited.")