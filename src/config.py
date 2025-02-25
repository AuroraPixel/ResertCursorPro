import os
import sys
import json
from typing import Dict, Any

class Config:
    _instance = None
    _config = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._config:
            self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            # 获取配置文件路径
            if getattr(sys, 'frozen', False):
                # 打包环境
                base_path = sys._MEIPASS
            else:
                # 开发环境
                base_path = os.path.dirname(os.path.dirname(__file__))
            
            config_path = os.path.join(base_path, 'config.json')
            
            # 如果配置文件存在，则加载
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            else:
                # 使用默认配置
                self._config = {
                    "api": {
                        "base_url": "http://localhost:8080",
                        "activate_endpoint": "/api/app/activate",
                        "account_endpoint": "/api/app/account",
                        "code_info_endpoint": "/api/app/code-info",
                        "timeout": 10,
                        "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjb2RlSWQiOjQsInN1YiI6ImFwcCIsImV4cCI6MTc0MDQ4NzI3MiwiaWF0IjoxNzQwNDAwODcyfQ.-AzN6SS3bn5wYzc64htCa1n_x-iGRYkD4p6zUVzHgEw"
                    }
                }
        except Exception as e:
            print(f"加载配置文件失败: {str(e)}")
            # 使用默认配置
            self._config = {
                "api": {
                    "base_url": "http://localhost:8080",
                    "activate_endpoint": "/api/app/activate",
                    "account_endpoint": "/api/app/account",
                    "code_info_endpoint": "/api/app/code-info",
                    "timeout": 10,
                    "auth_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJjb2RlSWQiOjQsInN1YiI6ImFwcCIsImV4cCI6MTc0MDQ4NzI3MiwiaWF0IjoxNzQwNDAwODcyfQ.-AzN6SS3bn5wYzc64htCa1n_x-iGRYkD4p6zUVzHgEw"
                }
            }
    
    @property
    def api_base_url(self) -> str:
        """获取API基础URL"""
        return self._config.get("api", {}).get("base_url", "http://localhost:8080")
    
    @property
    def api_url(self) -> str:
        """获取激活API的完整URL"""
        return f"{self.api_base_url}{self._config.get('api', {}).get('activate_endpoint', '/api/app/activate')}"
    
    @property
    def account_endpoint(self) -> str:
        """获取账号API的endpoint"""
        return self._config.get("api", {}).get("account_endpoint", "/api/app/account")
    
    @property
    def code_info_endpoint(self) -> str:
        """获取激活码信息API的endpoint"""
        return self._config.get("api", {}).get("code_info_endpoint", "/api/app/code-info")
    
    @property
    def auth_token(self) -> str:
        """获取认证token"""
        return self._config.get("api", {}).get("auth_token", "")
    
    @property
    def api_timeout(self) -> int:
        """获取API超时时间"""
        return self._config.get("api", {}).get("timeout", 10)
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置项"""
        return self._config.get(key, default)

# 创建全局配置实例
config = Config() 