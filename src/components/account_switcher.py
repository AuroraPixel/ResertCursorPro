import json
import os
import random
from typing import Dict, Optional, Tuple

from .cursor_auth_manager import CursorAuthManager
from .logger import logger

class AccountSwitcher:
    def __init__(self):
        self.auth_manager = CursorAuthManager()
        self.accounts_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'resources',
            'cursor_accounts.json'
        )
    
    def load_accounts(self) -> list:
        """
        从 JSON 文件加载账号信息
        
        Returns:
            list: 账号列表
        """
        try:
            if not os.path.exists(self.accounts_file):
                logger.error(f"账号配置文件不存在: {self.accounts_file}")
                return []
                
            with open(self.accounts_file, 'r', encoding='utf-8') as f:
                accounts = json.load(f)
                
            if not isinstance(accounts, list):
                logger.error("账号配置文件格式错误，应为账号列表")
                return []
                
            return accounts
                
        except json.JSONDecodeError:
            logger.error("账号配置文件格式错误")
            return []
        except Exception as e:
            logger.error(f"读取账号配置文件时出错: {str(e)}")
            return []
    
    def switch_account(self) -> Tuple[bool, Optional[Dict]]:
        """
        随机切换到一个新账号
        
        Returns:
            Tuple[bool, Optional[Dict]]: (是否成功, 账号信息)
        """
        accounts = self.load_accounts()
        if not accounts:
            logger.error("没有可用的账号")
            return False, None
        
        # 随机选择一个账号
        account = random.choice(accounts)
        
        try:
            # 提取账号信息
            email = account.get('email')
            access_token = account.get('access_token')
            refresh_token = account.get('refresh_token')
            
            if not all([email, access_token, refresh_token]):
                logger.error("账号信息不完整")
                return False, None
            
            # 更新认证信息
            logger.info(f"正在切换到账号: {email}")
            success = self.auth_manager.update_auth(
                email=email,
                access_token=access_token,
                refresh_token=refresh_token
            )
            
            if success:
                logger.info(f"成功切换到账号: {email}")
                return True, account
            else:
                logger.error(f"切换账号失败: {email}")
                return False, None
                
        except Exception as e:
            logger.error(f"切换账号时发生错误: {str(e)}")
            return False, None