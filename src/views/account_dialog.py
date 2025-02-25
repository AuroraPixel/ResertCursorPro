from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
    QFrame, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import concurrent.futures
import time
import subprocess
import sys
import os
from datetime import datetime

from src.components.account_service import AccountService
from src.components.cursor_auth_manager import CursorAuthManager
from src.components.logger import logger
from src.components.reset_machine import MachineIDResetter
from src.components.activation_service import ActivationService
from src.config import config

class AccountFetchThread(QThread):
    """获取账号列表的线程"""
    accounts_signal = pyqtSignal(bool, list, str)
    progress_signal = pyqtSignal(int, int)  # 当前进度，总数
    
    def run(self):
        try:
            account_service = AccountService()
            success, accounts, error_msg = account_service.get_accounts()
            
            if not success:
                self.accounts_signal.emit(False, [], error_msg)
                return
                
            # 获取每个账号的使用情况
            total_accounts = len(accounts)
            processed_accounts = []
            completed_count = 0
            
            # 过滤出有效的账号（字典类型且有访问令牌）
            valid_accounts = []
            for account in accounts:
                if isinstance(account, dict) and account.get('accessToken'):
                    valid_accounts.append(account)
                else:
                    if isinstance(account, dict):
                        logger.warning(f"账号 {account.get('email', '未知')} 没有访问令牌")
                    else:
                        logger.warning(f"跳过非字典类型的账号数据: {account}")
                    
                    # 为无效账号添加默认使用情况
                    if isinstance(account, dict):
                        account['usage'] = {
                            'premium': {'requests': 0, 'max_requests': 150},
                            'standard': {'requests': 0, 'max_requests': '∞'},
                            'unknown': {'requests': 0, 'max_requests': 50}
                        }
                        processed_accounts.append(account)
            
            # 使用线程池进行并发请求，最大并发数为5
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                # 提交所有任务
                future_to_account = {
                    executor.submit(self.fetch_account_info, account_service, account): 
                    account for account in valid_accounts
                }
                
                # 处理完成的任务
                for future in concurrent.futures.as_completed(future_to_account):
                    account = future_to_account[future]
                    try:
                        result = future.result()
                        processed_accounts.append(result)
                    except Exception as e:
                        logger.error(f"获取账号 {account.get('email', '未知')} 信息时出错: {str(e)}")
                        # 添加默认使用情况
                        account['usage'] = {
                            'premium': {'requests': 0, 'max_requests': 150},
                            'standard': {'requests': 0, 'max_requests': '∞'},
                            'unknown': {'requests': 0, 'max_requests': 50}
                        }
                        processed_accounts.append(account)
                    
                    # 更新进度
                    completed_count += 1
                    self.progress_signal.emit(completed_count, total_accounts)
            
            self.accounts_signal.emit(True, processed_accounts, "")
            
        except Exception as e:
            logger.error(f"获取账号列表出错: {str(e)}")
            self.accounts_signal.emit(False, [], str(e))
    
    def fetch_account_info(self, account_service, account):
        """获取单个账号的使用情况"""
        try:
            access_token = account.get('accessToken')
            email = account.get('email', '未知邮箱')
            
            # 获取用户信息
            user_info_success, user_info, user_info_error = account_service.get_user_info(access_token)
            if user_info_success:
                # 提取使用情况
                usage = user_info.get('usage', {})
                premium = usage.get('premium', {})
                standard = usage.get('standard', {})
                unknown = usage.get('unknown', {})
                
                # 添加使用情况到账号信息
                account['usage'] = {
                    'premium': {
                        'requests': premium.get('requests', 0),
                        'max_requests': premium.get('max_requests', 150)
                    },
                    'standard': {
                        'requests': standard.get('requests', 0),
                        'max_requests': '∞'  # 标准模型没有限制
                    },
                    'unknown': {
                        'requests': unknown.get('requests', 0),
                        'max_requests': unknown.get('max_requests', 50)
                    }
                }
            else:
                logger.warning(f"获取账号 {email} 的使用情况失败: {user_info_error}")
                account['usage'] = {
                    'premium': {'requests': 0, 'max_requests': 150},
                    'standard': {'requests': 0, 'max_requests': '∞'},
                    'unknown': {'requests': 0, 'max_requests': 50}
                }
        except Exception as e:
            logger.error(f"处理账号 {account.get('email', '未知')} 时出错: {str(e)}")
            account['usage'] = {
                'premium': {'requests': 0, 'max_requests': 150},
                'standard': {'requests': 0, 'max_requests': '∞'},
                'unknown': {'requests': 0, 'max_requests': 50}
            }
        
        return account

class AccountSwitchThread(QThread):
    """切换账号的线程"""
    finished_signal = pyqtSignal(bool, str)
    log_signal = pyqtSignal(str)
    
    def __init__(self, account):
        super().__init__()
        self.account = account
    
    def close_cursor_processes(self):
        """关闭所有Cursor进程"""
        self.log_signal.emit("正在关闭Cursor进程...")
        
        try:
            if sys.platform == "win32":  # Windows
                # 使用taskkill命令强制关闭所有Cursor进程
                subprocess.run(["taskkill", "/F", "/IM", "Cursor.exe"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["taskkill", "/F", "/IM", "Cursor Helper.exe"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["taskkill", "/F", "/IM", "Cursor Helper (Renderer).exe"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["taskkill", "/F", "/IM", "Cursor Helper (GPU).exe"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["taskkill", "/F", "/IM", "Cursor Helper (Plugin).exe"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            elif sys.platform == "darwin":  # macOS
                # 使用pkill命令关闭所有Cursor进程
                subprocess.run(["pkill", "-f", "Cursor"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            elif sys.platform == "linux":  # Linux
                # 使用pkill命令关闭所有Cursor进程
                subprocess.run(["pkill", "-f", "cursor"], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # 等待进程完全关闭
            time.sleep(2)
            self.log_signal.emit("Cursor进程已关闭")
            return True
        except Exception as e:
            self.log_signal.emit(f"关闭Cursor进程时出错: {str(e)}")
            return False
    
    def run(self):
        try:
            # 获取账号信息
            email = self.account.get('email')
            access_token = self.account.get('accessToken')
            refresh_token = self.account.get('refreshToken')
            
            if not all([email, access_token, refresh_token]):
                self.finished_signal.emit(False, "账号信息不完整")
                return
            
            # 1. 记录日志
            self.log_signal.emit(f"开始切换到账号: {email}")
            
            # 2. 关闭所有Cursor进程
            if not self.close_cursor_processes():
                self.log_signal.emit("警告: 关闭Cursor进程可能不完全，继续执行...")
            
            # 3. 创建重置器实例
            self.log_signal.emit("正在初始化机器码重置器...")
            resetter = MachineIDResetter()
            
            # 4. 重置机器码
            self.log_signal.emit("正在重置机器码...")
            reset_result = resetter.reset_machine_ids()
            
            if not reset_result:
                self.finished_signal.emit(False, "重置机器码失败")
                return
            
            self.log_signal.emit("机器码重置成功")
            
            # 5. 更新认证信息
            self.log_signal.emit("正在更新认证信息...")
            auth_manager = CursorAuthManager()
            success = auth_manager.update_auth(
                email=email,
                access_token=access_token,
                refresh_token=refresh_token
            )
            
            if success:
                self.log_signal.emit(f"成功切换到账号: {email}")
                self.finished_signal.emit(True, f"成功切换到账号: {email}")
            else:
                self.log_signal.emit("切换账号失败")
                self.finished_signal.emit(False, f"切换账号失败: {email}")
                
        except Exception as e:
            self.log_signal.emit(f"切换账号时发生错误: {str(e)}")
            self.finished_signal.emit(False, f"切换账号时发生错误: {str(e)}")

class CodeInfoThread(QThread):
    """获取激活码信息的线程"""
    info_signal = pyqtSignal(bool, dict, str)
    
    def __init__(self):
        super().__init__()
        self.activation_service = ActivationService()
    
    def run(self):
        try:
            # 使用当前的auth_token获取激活码
            auth_token = config.auth_token
            if not auth_token:
                logger.error("未找到有效的授权令牌")
                self.info_signal.emit(False, {}, "未找到有效的授权令牌")
                return
            
            logger.info(f"开始获取激活码信息，使用令牌: {auth_token[:10]}...")
            
            # 获取激活码信息
            # 注意：这里我们不传入具体的激活码，而是让服务器根据当前的auth_token返回对应的激活码信息
            success, data, error_msg = self.activation_service.get_code_info()
            
            if success and data:
                logger.info(f"CodeInfoThread获取到激活码信息: {data}")
                self.info_signal.emit(True, data, "")
            else:
                logger.error(f"CodeInfoThread获取激活码信息失败: {error_msg}")
                self.info_signal.emit(False, {}, error_msg or "获取激活码信息失败")
                
        except Exception as e:
            logger.error(f"获取激活码信息出错: {str(e)}")
            self.info_signal.emit(False, {}, str(e))

class CodeInfoDialog(QDialog):
    """激活码信息对话框"""
    
    def __init__(self, parent=None, code_info=None):
        super().__init__(parent)
        self.setWindowTitle("激活码信息")
        self.setMinimumSize(500, 400)  # 适当的窗口大小
        self.setModal(True)
        
        self.code_info = code_info
        self.code_info_thread = None
        
        self.setup_ui()
        
        # 如果没有传入激活码信息，则获取激活码信息
        if not self.code_info:
            self.fetch_code_info()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("激活码详细信息")
        title_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2196F3; margin-bottom: 20px;")
        layout.addWidget(title_label)
        
        # 信息卡片
        info_card = QFrame()
        info_card.setFrameShape(QFrame.Shape.StyledPanel)
        info_card.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 15px;
                border: 1px solid #e0e0e0;
                padding: 20px;
            }
        """)
        
        card_layout = QVBoxLayout(info_card)
        card_layout.setSpacing(15)
        
        # 激活码详细信息
        info_grid = QGridLayout()
        info_grid.setSpacing(15)
        info_grid.setContentsMargins(10, 10, 10, 10)
        
        # 创建标签
        labels = ["激活码:", "过期日期:", "最大账号数:", "已用账号数:", "状态:"]
        self.info_values = {}
        
        for i, label_text in enumerate(labels):
            label = QLabel(label_text)
            label.setStyleSheet("font-weight: bold; color: #555; font-size: 14px;")
            info_grid.addWidget(label, i, 0)
            
            value_label = QLabel("--")
            value_label.setStyleSheet("color: #333; font-size: 14px;")
            info_grid.addWidget(value_label, i, 1)
            self.info_values[label_text] = value_label
        
        card_layout.addLayout(info_grid)
        layout.addWidget(info_card)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # 不确定模式
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 20, 0, 0)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.refresh_btn.clicked.connect(self.fetch_code_info)
        
        self.close_btn = QPushButton("关闭")
        self.close_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 10px 30px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.close_btn.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        # 如果已有激活码信息，则更新显示
        if self.code_info:
            self.update_info_display()
    
    def fetch_code_info(self):
        """获取激活码信息"""
        self.progress_bar.setVisible(True)
        self.refresh_btn.setEnabled(False)
        
        self.code_info_thread = CodeInfoThread()
        self.code_info_thread.info_signal.connect(self.on_code_info_received)
        self.code_info_thread.start()
    
    def on_code_info_received(self, success, data, error_msg):
        """激活码信息获取完成的回调"""
        self.progress_bar.setVisible(False)
        self.refresh_btn.setEnabled(True)
        
        if success and data:
            self.code_info = data
            # 打印日志，帮助调试
            logger.info(f"获取到激活码信息: {data}")
            self.update_info_display()
        else:
            logger.error(f"获取激活码信息失败: {error_msg}")
            # 显示错误信息
            for key in self.info_values:
                self.info_values[key].setText("获取失败")
            
            QMessageBox.warning(self, "错误", f"获取激活码信息失败: {error_msg}")
    
    def update_info_display(self):
        """更新激活码信息显示"""
        if not self.code_info:
            return
        
        # 更新各个信息字段
        self.info_values["激活码:"].setText(self.code_info.get("code", "--"))
        
        # 格式化过期日期
        expires_at = self.code_info.get("expiresAt", "")
        if expires_at:
            try:
                # 假设日期格式为ISO 8601
                date_obj = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M:%S")
                self.info_values["过期日期:"].setText(formatted_date)
            except:
                self.info_values["过期日期:"].setText(expires_at)
        
        # 设置最大账号数和已用账号数
        max_accounts = self.code_info.get("maxAccounts", 0)
        used_accounts = self.code_info.get("usedAccounts", 0)
        
        self.info_values["最大账号数:"].setText(str(max_accounts))
        
        # 设置已用账号数，并根据使用情况设置颜色
        used_accounts_label = self.info_values["已用账号数:"]
        used_accounts_label.setText(str(used_accounts))
        
        # 如果已用账号数接近或达到最大账号数，改变颜色提示
        if max_accounts > 0:
            usage_ratio = used_accounts / max_accounts
            if usage_ratio >= 1:
                used_accounts_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
            elif usage_ratio >= 0.8:
                used_accounts_label.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
            else:
                used_accounts_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        
        # 设置状态，并根据状态设置颜色
        status = self.code_info.get("status", "")
        status_label = self.info_values["状态:"]
        status_label.setText(status)
        
        if status.lower() == "active" or status.lower() == "enabled":
            status_label.setStyleSheet("color: green; font-weight: bold; font-size: 14px;")
        elif status.lower() == "expired":
            status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        else:
            status_label.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")

class AccountDialog(QDialog):
    """账号选择对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择账号")
        self.setMinimumSize(600, 500)  # 减小窗口高度，因为移除了激活码信息
        self.setModal(True)
        
        self.accounts = []
        self.fetch_thread = None
        self.switch_thread = None
        self.code_info_thread = None
        self.main_window_log_callback = None
        self.code_info = None
        self.parent = parent
        
        self.setup_ui()
        
        # 获取账号列表
        self.fetch_accounts()
    
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel("账号列表")
        title_label.setFont(QFont('Arial', 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2196F3; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 账号列表
        self.account_list = QListWidget()
        self.account_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 10px;
                background-color: white;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 15px;
                border-bottom: 1px solid #eee;
                margin-bottom: 5px;
            }
            QListWidget::item:selected {
                background-color: #e3f2fd;
                color: #1976D2;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.account_list)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # 进度标签
        self.progress_label = QLabel("准备获取账号列表...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("color: #555; margin-top: 5px;")
        layout.addWidget(self.progress_label)
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #388E3C;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.refresh_btn.clicked.connect(self.fetch_accounts)
        
        self.switch_btn = QPushButton("切换")
        self.switch_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #BDBDBD;
            }
        """)
        self.switch_btn.clicked.connect(self.switch_account)
        self.switch_btn.setEnabled(False)
        
        self.info_btn = QPushButton("激活码信息")
        self.info_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.info_btn.clicked.connect(self.show_code_info)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
        """)
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.switch_btn)
        btn_layout.addWidget(self.info_btn)
        btn_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(btn_layout)
        
        # 连接信号
        self.account_list.itemSelectionChanged.connect(self.on_selection_changed)
    
    def show_code_info(self):
        """显示激活码信息对话框"""
        dialog = CodeInfoDialog(self, self.code_info)
        dialog.exec()
        # 如果激活码信息有更新，则更新本地缓存
        if dialog.code_info:
            self.code_info = dialog.code_info
    
    def fetch_accounts(self):
        """获取账号列表"""
        self.account_list.clear()
        self.accounts = []
        self.switch_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("正在获取账号列表...")
        self.progress_bar.setValue(0)
        
        self.fetch_thread = AccountFetchThread()
        self.fetch_thread.accounts_signal.connect(self.on_accounts_fetched)
        self.fetch_thread.progress_signal.connect(self.update_progress)
        self.fetch_thread.start()
    
    def update_progress(self, current, total):
        """更新进度条"""
        if total > 0:
            percent = int(current * 100 / total)
            self.progress_bar.setValue(percent)
            self.progress_label.setText(f"正在获取账号使用情况... ({current}/{total})")
    
    def on_accounts_fetched(self, success, accounts, error_msg):
        """账号列表获取完成的回调"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.refresh_btn.setEnabled(True)
        
        if success:
            self.accounts = accounts
            for account in accounts:
                # 确保account是字典类型
                if isinstance(account, dict):
                    email = account.get('email', '未知邮箱')
                    
                    # 获取使用情况
                    usage = account.get('usage', {})
                    premium = usage.get('premium', {})
                    standard = usage.get('standard', {})
                    unknown = usage.get('unknown', {})
                    
                    # 格式化显示文本
                    display_text = (
                        f"{email}\n"
                        f"高级模型: {premium.get('requests', 0)}/{premium.get('max_requests', 150)} "
                        f"标准: {standard.get('requests', 0)}/{standard.get('max_requests', '∞')} "
                        f"未知: {unknown.get('requests', 0)}/{unknown.get('max_requests', 50)}"
                    )
                    
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, account)
                    self.account_list.addItem(item)
                else:
                    logger.warning(f"跳过非字典类型的账号数据: {account}")
            
            if not accounts:
                QMessageBox.information(self, "提示", "没有找到任何账号")
            
            # 更新已用账号数
            if self.code_info:
                self.code_info["usedAccounts"] = len(accounts)
                self.update_info_display()
        else:
            QMessageBox.warning(self, "错误", f"获取账号列表失败: {error_msg}")
    
    def on_selection_changed(self):
        """选择变更时的回调"""
        # 根据是否有选中项来启用或禁用切换按钮
        self.switch_btn.setEnabled(len(self.account_list.selectedItems()) > 0)
        self.switch_btn.setToolTip("")
    
    def switch_account(self):
        """切换到选中的账号"""
        selected_items = self.account_list.selectedItems()
        if not selected_items:
            return
        
        selected_item = selected_items[0]
        account = selected_item.data(Qt.ItemDataRole.UserRole)
        
        # 显示确认对话框
        email = account.get('email', '未知邮箱')
        confirm = QMessageBox.question(
            self, 
            "确认切换账号", 
            f"您确定要切换到账号 {email} 吗？\n\n此操作将：\n1. 关闭所有Cursor进程\n2. 重置机器码\n3. 切换到新账号\n\n请确保已保存所有工作。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if confirm != QMessageBox.StandardButton.Yes:
            return
        
        # 禁用按钮
        self.switch_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)
        
        # 显示进度条和标签
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)
        self.progress_label.setText("正在准备切换账号...")
        self.progress_bar.setRange(0, 0)  # 设置为不确定模式
        
        # 启动切换线程
        self.switch_thread = AccountSwitchThread(account)
        self.switch_thread.finished_signal.connect(self.on_switch_finished)
        self.switch_thread.log_signal.connect(self.on_log_message)
        self.switch_thread.start()
    
    def on_switch_finished(self, success, message):
        """账号切换完成的回调"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.refresh_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)
        
        if success:
            QMessageBox.information(self, "成功", message)
            self.accept()  # 关闭对话框
        else:
            QMessageBox.warning(self, "错误", message)
            self.switch_btn.setEnabled(True)
    
    def on_log_message(self, message):
        """处理日志消息的回调"""
        logger.info(message)
        # 如果有主窗口日志回调，则发送日志到主窗口
        if self.main_window_log_callback:
            self.main_window_log_callback(message)
    
    def connect_log_to_main_window(self, log_callback):
        """连接日志到主窗口"""
        self.main_window_log_callback = log_callback 