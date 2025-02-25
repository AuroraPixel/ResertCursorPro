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
                # 打包环境下使用生产环境API地址
                production_api_url = "https://restar-cursor.zeabur.app"
            else:
                # 开发环境
                base_path = os.path.dirname(os.path.dirname(__file__))
                # 开发环境使用本地API地址
                production_api_url = "http://localhost:8080"
            
            config_path = os.path.join(base_path, 'config.json')
            
            # 如果配置文件存在，则加载
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                    
                # 如果是打包环境，强制使用生产环境API地址
                if getattr(sys, 'frozen', False):
                    self._config["api"]["base_url"] = production_api_url
            else:
                # 使用默认配置
                self._config = {
                    "api": {
                        "base_url": production_api_url,
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
            # 根据环境选择合适的API地址
            default_api_url = "https://restar-cursor.zeabur.app" if getattr(sys, 'frozen', False) else "http://localhost:8080"
            self._config = {
                "api": {
                    "base_url": default_api_url,
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
        # 如果是打包环境，强制返回生产环境API地址
        if getattr(sys, 'frozen', False):
            return "https://restar-cursor.zeabur.app"
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