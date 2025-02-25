from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox,
    QFrame, QGridLayout, QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon
import os
import sys
from datetime import datetime
from src.components.activation_service import ActivationService
from src.components.logger import logger
import json

def get_resource_path(relative_path):
    """获取资源文件的绝对路径"""
    if getattr(sys, 'frozen', False):
        # 如果是打包后的环境
        base_path = sys._MEIPASS
    else:
        # 如果是开发环境
        base_path = os.path.abspath(".")
    
    return os.path.join(base_path, relative_path)

class LoginWindow(QMainWindow):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.activation_service = ActivationService()
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("ResertCursorPro")
        self.setFixedSize(500, 400)
        
        # 设置窗口图标
        icon_path = get_resource_path('resources/icon.ico')
        self.setWindowIcon(QIcon(icon_path))
        
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # 添加标题
        title_label = QLabel("ResertCursorPro")
        title_label.setFont(QFont('Arial', 24, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #2196F3;")
        layout.addWidget(title_label)
        
        # 创建表单布局
        form_widget = QWidget()
        form_layout = QVBoxLayout(form_widget)
        form_layout.setSpacing(15)
        
        # 授权码输入
        auth_label = QLabel("请输入授权码")
        auth_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        auth_label.setStyleSheet("color: #666; font-size: 14px;")
        form_layout.addWidget(auth_label)
        
        self.auth_input = QLineEdit()
        self.auth_input.setPlaceholderText("授权码")
        self.auth_input.setStyleSheet(self.get_input_style())
        self.auth_input.setMaxLength(32)  # 限制最大长度
        form_layout.addWidget(self.auth_input)
        
        # 验证按钮
        verify_btn = QPushButton("验证授权")
        verify_btn.setStyleSheet(self.get_button_style())
        verify_btn.clicked.connect(self.verify_auth)
        form_layout.addWidget(verify_btn)
        
        layout.addWidget(form_widget)
        layout.addStretch()
        
        # 设置窗口样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: white;
            }
        """)
        
        # 设置回车键触发验证
        self.auth_input.returnPressed.connect(verify_btn.click)
    
    def get_input_style(self):
        return """
            QLineEdit {
                padding: 12px;
                border: 2px solid #ddd;
                border-radius: 6px;
                font-size: 16px;
                text-align: center;
            }
            QLineEdit:focus {
                border: 2px solid #2196F3;
            }
        """
    
    def get_button_style(self, secondary=False):
        if secondary:
            return """
                QPushButton {
                    background-color: #78909C;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #607D8B;
                }
                QPushButton:pressed {
                    background-color: #455A64;
                }
            """
        else:
            return """
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 12px;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                    min-width: 120px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """
    
    def verify_auth(self):
        auth_code = self.auth_input.text().strip()
        
        if not auth_code:
            QMessageBox.warning(self, "验证失败", "请输入授权码！")
            return
        
        # 调用激活服务验证授权码
        success, data, error_msg = self.activation_service.activate(auth_code)
        
        if success:
            # 保存令牌信息到配置文件
            token = data.get("token")
            expires_at = data.get("expiresAt")
            logger.info(f"授权成功，过期时间: {expires_at}")
            
            # 将token保存到config中
            from src.config import config
            config._config["api"]["auth_token"] = token
            
            # 保存配置到文件
            try:
                if getattr(sys, 'frozen', False):
                    # 打包环境
                    base_path = sys._MEIPASS
                else:
                    # 开发环境
                    base_path = os.path.dirname(os.path.dirname(__file__))
                
                config_path = os.path.join(base_path, 'config.json')
                
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config._config, f, indent=4)
                
                logger.info(f"授权令牌已保存到配置文件: {config_path}")
            except Exception as e:
                logger.error(f"保存配置文件失败: {str(e)}")
            
            # 验证成功，进入主界面
            self.on_login_success()
            self.close()
        else:
            QMessageBox.warning(self, "验证失败", error_msg or "激活失败，请检查授权码！") 