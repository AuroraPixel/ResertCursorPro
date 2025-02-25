from datetime import datetime
import sys
import os
import asyncio
from io import StringIO
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QLineEdit,
    QFrame, QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
import time

from src.components.reset_machine import MachineIDResetter
from src.components.exit_cursor import ExitCursor
from src.components.account_switcher import AccountSwitcher
from src.components.register_account import AccountRegister
from src.components.account_service import AccountService
from src.views.account_dialog import AccountDialog
from src.components.logger import logger, set_ui_log_callback
from src.components.activation_service import ActivationService

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

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

class GetAccountThread(QThread):
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        # 设置UI日志回调
        set_ui_log_callback(self.handle_log)

    def handle_log(self, log_entry):
        """处理来自logger的日志"""
        # 提取日志消息部分
        if " - INFO: " in log_entry:
            message = log_entry.split(" - INFO: ")[1]
            # 只发送包含Step的日志
            if "Step" in message:
                self.log_signal.emit(message)
        elif " - ERROR: " in log_entry:
            message = log_entry.split(" - ERROR: ")[1]
            self.log_signal.emit(f"❌ {message}")
        elif " - WARNING: " in log_entry:
            message = log_entry.split(" - WARNING: ")[1]
            self.log_signal.emit(f"⚠️ {message}")

    def run(self):
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                retry_count += 1
                self.log_signal.emit(f"\n=== 第 {retry_count} 次尝试 ===")
                
                # 创建账号注册器
                register = AccountRegister()
                
                # 注册账号
                self.log_signal.emit("开始获取新账号...")
                success = asyncio.run(register.register_single_account())
                
                if success:
                    self.log_signal.emit("✅ 账号注册成功")
                    
                    # 上传账号信息
                    self.log_signal.emit("\n正在上传账号信息...")
                    account_service = AccountService()
                    
                    # 创建账号信息
                    account_info = {
                        "email": register.account,
                        "email_password": register.email_password,
                        "cursor_password": register.cursor_password,
                        "access_token": register.cursor_token,
                        "refresh_token": register.cursor_token  # 这里使用相同的token
                    }
                    
                    upload_success, error_msg = account_service.upload_account(account_info)
                    
                    if upload_success:
                        self.log_signal.emit("✅ 账号信息上传成功")
                        self.finished_signal.emit(True)
                        return
                    else:
                        self.log_signal.emit(f"❌ 账号信息上传失败: {error_msg}")
                        # 如果是最后一次尝试，则返回失败
                        if retry_count >= max_retries:
                            self.finished_signal.emit(False)
                            return
                else:
                    self.log_signal.emit("❌ 账号注册失败")
                    # 如果是最后一次尝试，则返回失败
                    if retry_count >= max_retries:
                        self.log_signal.emit(f"\n=== 已达到最大重试次数 ({max_retries} 次)，操作失败 ===")
                        self.finished_signal.emit(False)
                        return
                    else:
                        self.log_signal.emit("等待 5 秒后进行下一次尝试...")
                        time.sleep(5)

            except Exception as e:
                self.log_signal.emit(f"❌ 获取账号过程出错: {str(e)}")
                # 如果是最后一次尝试，则返回失败
                if retry_count >= max_retries:
                    self.log_signal.emit(f"\n=== 已达到最大重试次数 ({max_retries} 次)，操作失败 ===")
                    self.finished_signal.emit(False)
                    return
                else:
                    self.log_signal.emit("等待 5 秒后进行下一次尝试...")
                    time.sleep(5)

        # 如果所有重试都失败了
        self.log_signal.emit(f"\n=== 所有重试都失败了 ({max_retries} 次) ===")
        self.finished_signal.emit(False)

class MethodWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.reset_thread = None
        self.restore_thread = None
        self.get_account_thread = None
        self.cursor_path = None
        self.code_info = None
        
        # 创建账号服务实例
        from src.components.account_service import AccountService
        self.account_service = AccountService()
        
        self.setup_ui()
        
        # 获取激活码信息
        self.fetch_code_info()
    
    def setup_ui(self):
        self.setWindowTitle("ResertCursorPro")
        self.setMinimumSize(800, 600)
        
        # 设置窗口图标
        icon_path = get_resource_path('resources/icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        
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
        title_label = QLabel("ResertCursorPro")
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
        
        # 恢复备份按钮
        self.restore_btn = QPushButton("恢复备份")
        self.restore_btn.setMinimumHeight(50)
        self.restore_btn.setStyleSheet(self.get_button_style("warning"))
        self.restore_btn.clicked.connect(self.restore_backup)
        btn_layout.addWidget(self.restore_btn)
        
        # 在按钮容器中添加获取账号按钮
        self.get_account_btn = QPushButton("获取账号")
        self.get_account_btn.setMinimumHeight(50)
        self.get_account_btn.setStyleSheet(self.get_button_style("primary"))
        self.get_account_btn.clicked.connect(self.get_account)
        btn_layout.addWidget(self.get_account_btn)
        
        # 添加切换账号按钮
        self.switch_account_btn = QPushButton("切换账号")
        self.switch_account_btn.setMinimumHeight(50)
        self.switch_account_btn.setStyleSheet(self.get_button_style("info"))
        self.switch_account_btn.clicked.connect(self.show_account_dialog)
        btn_layout.addWidget(self.switch_account_btn)
        
        # 添加激活码信息按钮
        self.code_info_btn = QPushButton("激活码信息")
        self.code_info_btn.setMinimumHeight(50)
        self.code_info_btn.setStyleSheet(self.get_button_style("warning"))
        self.code_info_btn.clicked.connect(self.show_code_info_dialog)
        btn_layout.addWidget(self.code_info_btn)
        
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
        
        # 启动定时器，定期检查用户状态
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.check_user_status_silently)
        self.status_timer.start(6000)  # 每分钟检查一次
    
    def check_user_status_silently(self):
        """
        静默检查用户状态，不显示消息框，用于定时检查
        """
        from src.components.logger import logger
        from src.config import config
        from datetime import datetime
        
        # 检查授权令牌
        auth_token = config.auth_token
        if not auth_token:
            logger.error("定时检查: 未找到有效的授权令牌")
            self.disable_all_buttons("未找到有效的授权令牌，请重新登录")
            return False
        
        # 使用 activation_service 获取激活码信息
        activation_service = ActivationService()
        success, code_info, error_msg = activation_service.get_code_info()
        
        if not success:
            logger.error(f"定时检查: 获取激活码信息失败: {error_msg}")
            self.disable_all_buttons(f"网络连接失败或授权已过期: {error_msg}")
            return False
        
        # 更新本地激活码信息缓存
        self.code_info = code_info
        
        # 检查账号是否过期 - 根据 expiresAt 字段与当前时间比较
        expires_at_str = code_info.get("expiresAt", "")
        if expires_at_str:
            try:
                # 解析过期时间字符串，格式如: "2025-02-28T18:45:06+08:00"
                expires_at = datetime.fromisoformat(expires_at_str)
                # 将带时区的datetime转换为不带时区的datetime
                if expires_at.tzinfo is not None:
                    # 转换为UTC时间，然后去掉时区信息
                    expires_at = expires_at.astimezone().replace(tzinfo=None)
                now = datetime.now()
                
                if now > expires_at:
                    logger.error("定时检查: 授权已过期")
                    self.disable_all_buttons("授权已过期，请重新激活")
                    return False
            except ValueError as e:
                logger.error(f"定时检查: 解析过期时间出错: {str(e)}")
                # 如果无法解析时间，我们不应该阻止用户使用
        
        # 检查状态是否启用
        status = code_info.get("status", "")
        if status != "enabled":
            logger.error(f"定时检查: 账号状态异常: {status}")
            self.disable_all_buttons(f"账号状态异常: {status}")
            return False
        
        # 恢复按钮状态
        self.enable_all_buttons()
        return True
    
    def disable_all_buttons(self, reason):
        """
        禁用所有功能按钮
        
        Args:
            reason: 禁用原因
        """
        self.restore_btn.setEnabled(False)
        self.get_account_btn.setEnabled(False)
        self.switch_account_btn.setEnabled(False)
        self.code_info_btn.setEnabled(False)
        
        # 设置提示信息
        self.restore_btn.setToolTip(reason)
        self.get_account_btn.setToolTip(reason)
        self.switch_account_btn.setToolTip(reason)
        self.code_info_btn.setToolTip(reason)
        
        # 添加日志
        self.log_area.append_log(f"功能已禁用: {reason}")
    
    def enable_all_buttons(self):
        """恢复所有按钮状态"""
        self.restore_btn.setEnabled(True)
        self.switch_account_btn.setEnabled(True)
        self.code_info_btn.setEnabled(True)
        
        # 清除提示信息
        self.restore_btn.setToolTip("")
        self.switch_account_btn.setToolTip("")
        self.code_info_btn.setToolTip("")
        
        # 根据激活码信息决定是否启用获取账号按钮
        if self.code_info:
            max_accounts = self.code_info.get("maxAccounts", 0)
            used_accounts = self.code_info.get("usedAccounts", 0)
            
            if used_accounts >= max_accounts and max_accounts > 0:
                self.get_account_btn.setEnabled(False)
                self.get_account_btn.setToolTip(f"已达到最大账号数限制 ({used_accounts}/{max_accounts})")
            else:
                self.get_account_btn.setEnabled(True)
                self.get_account_btn.setToolTip("")
        else:
            self.get_account_btn.setEnabled(True)
            self.get_account_btn.setToolTip("")
    
    def verify_user_status(self) -> bool:
        """
        验证用户状态，检查网络连接和账号是否过期
        
        Returns:
            bool: 验证是否通过
        """
        from src.components.logger import logger
        from src.config import config
        from datetime import datetime
        from src.components.activation_service import ActivationService
        
        self.log_area.append_log("正在验证用户状态...")
        
        # 检查授权令牌
        auth_token = config.auth_token
        if not auth_token:
            logger.error("未找到有效的授权令牌")
            self.log_area.append_log("未找到有效的授权令牌，请重新登录")
            QMessageBox.critical(self, "验证失败", "未找到有效的授权令牌，请重新登录")
            self.disable_all_buttons("未找到有效的授权令牌，请重新登录")
            return False
        
        # 使用 activation_service 获取激活码信息
        activation_service = ActivationService()
        success, code_info, error_msg = activation_service.get_code_info()
        
        if not success:
            logger.error(f"获取激活码信息失败: {error_msg}")
            self.log_area.append_log(f"网络连接失败或授权已过期: {error_msg}")
            QMessageBox.critical(self, "验证失败", f"网络连接失败或授权已过期: {error_msg}")
            self.disable_all_buttons(f"网络连接失败或授权已过期: {error_msg}")
            return False
        
        # 更新本地激活码信息缓存
        self.code_info = code_info
        
        # 检查账号是否过期 - 根据 expiresAt 字段与当前时间比较
        expires_at_str = code_info.get("expiresAt", "")
        if expires_at_str:
            try:
                # 解析过期时间字符串，格式如: "2025-02-28T18:45:06+08:00"
                expires_at = datetime.fromisoformat(expires_at_str)
                # 将带时区的datetime转换为不带时区的datetime
                if expires_at.tzinfo is not None:
                    # 转换为UTC时间，然后去掉时区信息
                    expires_at = expires_at.astimezone().replace(tzinfo=None)
                now = datetime.now()
                
                if now > expires_at:
                    logger.error("授权已过期")
                    self.log_area.append_log("授权已过期，请重新激活")
                    QMessageBox.critical(self, "验证失败", "授权已过期，请重新激活")
                    self.disable_all_buttons("授权已过期，请重新激活")
                    return False
            except ValueError as e:
                logger.error(f"解析过期时间出错: {str(e)}")
                self.log_area.append_log(f"解析过期时间出错: {str(e)}")
                # 如果无法解析时间，我们不应该阻止用户使用
        
        # 检查状态是否启用
        status = code_info.get("status", "")
        if status != "enabled":
            logger.error(f"账号状态异常: {status}")
            self.log_area.append_log(f"账号状态异常: {status}")
            QMessageBox.critical(self, "验证失败", f"账号状态异常: {status}")
            self.disable_all_buttons(f"账号状态异常: {status}")
            return False
        
        # 确保按钮状态正确
        self.enable_all_buttons()
        
        self.log_area.append_log("用户状态验证通过")
        return True
    
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
        elif style_type == "info":
            return """
                QPushButton {
                    background-color: #009688;
                    color: white;
                    border: none;
                    padding: 15px 30px;
                    border-radius: 8px;
                    font-size: 16px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #00796B;
                }
                QPushButton:pressed {
                    background-color: #004D40;
                }
                QPushButton:disabled {
                    background-color: #BDBDBD;
                }
            """
    
    def restore_backup(self):
        """恢复备份"""
        # 验证用户状态
        if not self.verify_user_status():
            return
            
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
            self.restore_btn.setEnabled(False)
            self.restore_btn.setText("恢复中...")
            
            # 创建并启动恢复线程
            self.restore_thread = RestoreThread()
            self.restore_thread.log_signal.connect(self.log_area.append_log)
            self.restore_thread.finished_signal.connect(self.on_restore_finished)
            self.restore_thread.start()
    
    def on_restore_finished(self, success):
        # 恢复按钮状态
        self.restore_btn.setEnabled(True)
        self.restore_btn.setText("恢复备份")
        
        if not success:
            self.log_area.append_log("恢复失败，请查看上方日志了解详细信息。")
    
    def get_account(self):
        """获取新账号"""
        # 验证用户状态
        if not self.verify_user_status():
            return
            
        # 显示确认对话框
        reply = QMessageBox.question(
            self,
            "确认操作",
            "此操作将获取一个新的Cursor账号，是否继续？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # 清空日志区域
            self.log_area.clear_logs()
            
            # 禁用所有按钮，防止重复点击
            self.get_account_btn.setEnabled(False)
            self.get_account_btn.setText("正在获取账号...")
            self.restore_btn.setEnabled(False)
            self.switch_account_btn.setEnabled(False)
            self.code_info_btn.setEnabled(False)
            
            # 显示日志区域
            self.log_area.setVisible(True)
            
            # 添加初始日志
            self.log_area.append_log("开始获取新账号...")
            
            # 创建并启动线程
            self.get_account_thread = GetAccountThread()
            
            # 连接信号
            self.get_account_thread.log_signal.connect(self.log_area.append_log)
            self.get_account_thread.finished_signal.connect(self.on_get_account_finished)
            
            # 启动线程
            self.get_account_thread.start()
    
    def on_get_account_finished(self, success):
        # 恢复按钮状态
        self.get_account_btn.setText("获取账号")
        
        # 重新获取激活码信息，更新按钮状态
        self.fetch_code_info()
        
        if not success:
            self.log_area.append_log("获取账号失败，请查看上方日志了解详细信息。")
    
    def show_account_dialog(self):
        """显示账号选择对话框"""
        # 验证用户状态
        if not self.verify_user_status():
            return
            
        # 清空日志
        self.log_area.clear_logs()
        self.log_area.append_log("开始账号切换流程...")
        
        dialog = AccountDialog(self)
        # 连接日志信号到主窗口的日志区域
        dialog.connect_log_to_main_window(self.log_area.append_log)
        result = dialog.exec()
        
        if result == QDialog.DialogCode.Accepted:
            self.log_area.append_log("账号切换成功")
        else:
            self.log_area.append_log("取消账号切换")

    def show_code_info_dialog(self):
        """显示激活码信息对话框"""
        # 验证用户状态
        if not self.verify_user_status():
            return
            
        from src.views.account_dialog import CodeInfoDialog
        
        dialog = CodeInfoDialog(self, self.code_info)
        dialog.exec()
        
        # 如果激活码信息有更新，则更新本地缓存
        if dialog.code_info:
            self.code_info = dialog.code_info
            # 更新UI，如果已用账号数已达到或超过最大账号数，禁用获取账号按钮
            max_accounts = self.code_info.get("maxAccounts", 0)
            used_accounts = self.code_info.get("usedAccounts", 0)
            
            if used_accounts >= max_accounts and max_accounts > 0:
                self.get_account_btn.setEnabled(False)
                self.get_account_btn.setToolTip(f"已达到最大账号数限制 ({used_accounts}/{max_accounts})")
                self.log_area.append_log(f"已达到最大账号数限制: {used_accounts}/{max_accounts}")
            else:
                self.get_account_btn.setEnabled(True)
                self.get_account_btn.setToolTip("")

    def fetch_code_info(self):
        """获取激活码信息"""
        self.log_area.append_log("正在获取激活码信息...")
        
        # 创建激活服务实例
        from src.components.activation_service import ActivationService
        from src.components.logger import logger
        from src.config import config
        
        # 检查授权令牌
        auth_token = config.auth_token
        if not auth_token:
            logger.error("未找到有效的授权令牌")
            self.log_area.append_log("未找到有效的授权令牌，无法获取激活码信息")
            self.disable_all_buttons("未找到有效的授权令牌，请重新登录")
            return False
        
        # 获取激活码信息
        activation_service = ActivationService()
        success, code_info, error_msg = activation_service.get_code_info()
        
        if not success:
            logger.error(f"获取激活码信息失败: {error_msg}")
            self.log_area.append_log(f"获取激活码信息失败: {error_msg}")
            self.disable_all_buttons(f"网络连接失败或授权已过期: {error_msg}")
            return False
        
        # 更新本地激活码信息缓存
        self.code_info = code_info
        
        # 检查账号是否过期 - 根据 expiresAt 字段与当前时间比较
        expires_at_str = code_info.get("expiresAt", "")
        if expires_at_str:
            try:
                # 解析过期时间字符串，格式如: "2025-02-28T18:45:06+08:00"
                expires_at = datetime.fromisoformat(expires_at_str)
                # 将带时区的datetime转换为不带时区的datetime
                if expires_at.tzinfo is not None:
                    # 转换为UTC时间，然后去掉时区信息
                    expires_at = expires_at.astimezone().replace(tzinfo=None)
                now = datetime.now()
                
                if now > expires_at:
                    logger.error("授权已过期")
                    self.log_area.append_log("授权已过期，请重新激活")
                    self.disable_all_buttons("授权已过期，请重新激活")
                    return False
            except ValueError as e:
                logger.error(f"解析过期时间出错: {str(e)}")
                # 如果无法解析时间，我们不应该阻止用户使用
        
        # 检查状态是否启用
        status = code_info.get("status", "")
        if status != "enabled":
            logger.error(f"账号状态异常: {status}")
            self.log_area.append_log(f"账号状态异常: {status}")
            self.disable_all_buttons(f"账号状态异常: {status}")
            return False
            
        # 记录获取到的激活码信息
        logger.info(f"获取到激活码信息: {code_info}")
        self.log_area.append_log("激活码信息获取成功")
        self.log_area.append_log(f"激活码: {code_info.get('code', '--')}")
        self.log_area.append_log(f"过期时间: {code_info.get('expiresAt', '--')}")
        self.log_area.append_log(f"账号数量: {code_info.get('usedAccounts', 0)}/{code_info.get('maxAccounts', 0)}")
        
        # 检查账号数量限制
        max_accounts = code_info.get("maxAccounts", 0)
        used_accounts = code_info.get("usedAccounts", 0)
        
        # 如果已用账号数已达到或超过最大账号数，禁用获取账号按钮
        if used_accounts >= max_accounts and max_accounts > 0:
            self.get_account_btn.setEnabled(False)
            self.get_account_btn.setToolTip(f"已达到最大账号数限制 ({used_accounts}/{max_accounts})")
            self.log_area.append_log(f"已达到最大账号数限制: {used_accounts}/{max_accounts}")
        else:
            self.get_account_btn.setEnabled(True)
            self.get_account_btn.setToolTip("")
            
        return True 