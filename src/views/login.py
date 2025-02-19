from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout,
    QLabel, QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

class LoginWindow(QMainWindow):
    def __init__(self, on_login_success):
        super().__init__()
        self.on_login_success = on_login_success
        self.setup_ui()
    
    def setup_ui(self):
        self.setWindowTitle("ResertCursorPro")
        self.setFixedSize(400, 300)
        
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
    
    def get_button_style(self):
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
        
        # 这里添加实际的授权码验证逻辑
        if auth_code == "1":  # 示例验证
            self.on_login_success()
            self.close()
        else:
            QMessageBox.warning(self, "验证失败", "无效的授权码！") 