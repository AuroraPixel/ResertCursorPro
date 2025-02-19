from datetime import datetime
import sys
import os
from io import StringIO
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QFrame, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

from components.reset_machine import MachineIDResetter
from components.exit_cursor import ExitCursor
from components.account_switcher import AccountSwitcher

class LogArea(QTextEdit):
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
        self.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
                font-family: 'Courier New', monospace;
            }
        """)
    
    def append_log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"{timestamp} {message}"
        self.append(formatted_message)
    
    def clear_logs(self):
        """清空日志区域"""
        self.clear()

class ResetThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def run(self):
        output_buffer = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_buffer

        try:
            # 先执行 ExitCursor
            self.log_signal.emit("正在关闭 Cursor...")
            success, cursor_path = ExitCursor()
            
            # 获取 ExitCursor 的输出
            output = output_buffer.getvalue()
            output_buffer.truncate(0)
            output_buffer.seek(0)
            
            # 发送 ExitCursor 的日志
            for line in output.split('\n'):
                if line.strip():
                    self.log_signal.emit(line.strip())
            
            if not success:
                self.log_signal.emit("无法完全关闭 Cursor，请手动关闭后重试。")
                self.finished_signal.emit(False)
                return
            
            # 执行重置机器码
            resetter = MachineIDResetter()
            result = resetter.reset_machine_ids()
            
            # 获取重置操作的输出
            output = output_buffer.getvalue()
            output_buffer.truncate(0)
            output_buffer.seek(0)
            
            for line in output.split('\n'):
                if line.strip():
                    self.log_signal.emit(line.strip())
            
            if not result:
                self.finished_signal.emit(False)
                return
            
            # 切换账号
            self.log_signal.emit("\n正在切换账号...")
            account_switcher = AccountSwitcher()
            success, account = account_switcher.switch_account()
            
            # 获取账号切换的输出
            output = output_buffer.getvalue()
            for line in output.split('\n'):
                if line.strip():
                    self.log_signal.emit(line.strip())
            
            if success and account:
                self.log_signal.emit(f"账号切换成功: {account['email']}")
            else:
                self.log_signal.emit("账号切换失败")
            
            self.finished_signal.emit(success)

        finally:
            sys.stdout = original_stdout
            output_buffer.close()

class RestoreThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def run(self):
        output_buffer = StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_buffer

        try:
            resetter = MachineIDResetter()
            result = resetter.restore_machine_ids()
            
            # 获取捕获的输出并发送日志信号
            output = output_buffer.getvalue()
            for line in output.split('\n'):
                if line.strip():
                    self.log_signal.emit(line.strip())
            
            self.finished_signal.emit(result)

        finally:
            sys.stdout = original_stdout
            output_buffer.close()

class MethodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.reset_thread = None
        self.restore_thread = None
        self.cursor_path = None
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("Cursor Tool")
        self.setMinimumSize(800, 600)
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(20)
        
        # 添加 CURSOR 标题
        title_label = QLabel("CURSOR")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_layout.addWidget(title_label)
        
        # Windows 环境下添加路径输入
        if sys.platform == "win32":
            path_container = QWidget()
            path_layout = QVBoxLayout(path_container)
            
            path_label = QLabel("Cursor 安装路径:")
            path_label.setStyleSheet("color: #666; font-size: 14px;")
            path_layout.addWidget(path_label)
            
            self.path_input = QLineEdit()
            default_path = os.path.join(os.getenv("LOCALAPPDATA", ""), "Programs", "Cursor")
            self.path_input.setPlaceholderText(default_path)
            self.path_input.setStyleSheet("""
                QLineEdit {
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QLineEdit:focus {
                    border: 1px solid #2196F3;
                }
            """)
            path_layout.addWidget(self.path_input)
            
            left_layout.addWidget(path_container)
        
        # 按钮容器
        btn_container = QWidget()
        btn_container.setMaximumWidth(200)
        btn_layout = QVBoxLayout(btn_container)
        btn_layout.setSpacing(15)
        
        # 重置机器码按钮
        self.reset_btn = QPushButton("重置机器码")
        self.reset_btn.setMinimumHeight(50)
        self.reset_btn.setStyleSheet(self.get_button_style())
        self.reset_btn.clicked.connect(self.reset_machine_code)
        btn_layout.addWidget(self.reset_btn)
        
        # 恢复备份按钮
        self.restore_btn = QPushButton("恢复备份")
        self.restore_btn.setMinimumHeight(50)
        self.restore_btn.setStyleSheet(self.get_button_style("warning"))
        self.restore_btn.clicked.connect(self.restore_backup)
        btn_layout.addWidget(self.restore_btn)
        
        left_layout.addWidget(btn_container, alignment=Qt.AlignmentFlag.AlignCenter)
        left_layout.addStretch()
        
        # 右侧日志面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        log_label = QLabel("运行日志")
        log_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        log_label.setStyleSheet("font-weight: bold; font-size: 16px; color: #333;")
        right_layout.addWidget(log_label)
        
        self.log_area = LogArea()
        right_layout.addWidget(self.log_area)
        
        # 添加左右面板到主布局
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 2)
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
            QLabel {
                color: #333;
                font-size: 14px;
            }
            QTextEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                background-color: white;
            }
        """)
        
        # 添加初始日志
        self.log_area.append_log("程序已启动，等待操作...")
    
    def get_button_style(self, style_type="primary"):
        if style_type == "primary":
            return """
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                }
            """
        elif style_type == "warning":
            return """
                QPushButton {
                    background-color: #FF9800;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #F57C00;
                }
                QPushButton:pressed {
                    background-color: #E65100;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                }
            """
    
    def reset_machine_code(self):
        # Windows 环境下检查路径
        if sys.platform == "win32":
            cursor_path = self.path_input.text().strip() or self.path_input.placeholderText()
            if not os.path.exists(cursor_path):
                QMessageBox.warning(self, "路径错误", "请输入正确的 Cursor 安装路径！")
                return
            
            # 设置环境变量
            os.environ["CURSOR_PATH"] = cursor_path
        
        # 清空日志
        self.log_area.clear_logs()
        self.log_area.append_log("程序已启动，等待操作...")
        
        # 禁用所有按钮
        self.reset_btn.setEnabled(False)
        self.restore_btn.setEnabled(False)
        self.reset_btn.setText("重置中...")
        
        # 创建并启动重置线程
        self.reset_thread = ResetThread()
        self.reset_thread.log_signal.connect(self.log_area.append_log)
        self.reset_thread.finished_signal.connect(self.on_reset_finished)
        self.reset_thread.start()
    
    def restore_backup(self):
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            '确认恢复',
            '确定要恢复到备份的机器码吗？此操作不可撤销。',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志
            self.log_area.clear_logs()
            self.log_area.append_log("程序已启动，等待操作...")
            
            # 禁用所有按钮
            self.reset_btn.setEnabled(False)
            self.restore_btn.setEnabled(False)
            self.restore_btn.setText("恢复中...")
            
            # 创建并启动恢复线程
            self.restore_thread = RestoreThread()
            self.restore_thread.log_signal.connect(self.log_area.append_log)
            self.restore_thread.finished_signal.connect(self.on_restore_finished)
            self.restore_thread.start()
    
    def on_reset_finished(self, success):
        # 恢复按钮状态
        self.reset_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.reset_btn.setText("重置机器码")
        
        if not success:
            self.log_area.append_log("重置失败，请查看上方日志了解详细信息。")
    
    def on_restore_finished(self, success):
        # 恢复按钮状态
        self.reset_btn.setEnabled(True)
        self.restore_btn.setEnabled(True)
        self.restore_btn.setText("恢复备份")
        
        if not success:
            self.log_area.append_log("恢复失败，请查看上方日志了解详细信息。") 