import requests
from typing import Dict, Tuple, List
from src.config import config
from .logger import logger

class AccountService:
    def __init__(self):
        self.api_url = f"{config.api_base_url}{config.account_endpoint}"
        self.auth_token = config.auth_token
        self.user_info_url = "https://cc.wisdgod.com/userinfo"
        self.checksum_url = "https://cc.wisdgod.com/get-checksum"
    
    def upload_account(self, account_info: Dict) -> Tuple[bool, str]:
        """
        上传账号信息到服务器
        
        Args:
            account_info: 账号信息字典，包含邮箱、密码等信息
            
        Returns:
            Tuple[bool, str]: (是否成功, 错误信息)
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "email": account_info["email"],
                "emailPassword": account_info["email_password"],
                "cursorPassword": account_info["cursor_password"],
                "accessToken": account_info.get("access_token", ""),
                "refreshToken": account_info.get("refresh_token", "")
            }
            
            #logger.info("正在上传账号信息...")
            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                timeout=config.api_timeout
            )
            
            if response.status_code == 200:
                #logger.info("账号信息上传成功")
                return True, ""
            else:
                error_msg = response.json().get("message", "获取账号失败")
                logger.error(f"获取账号失败: {error_msg}")
                return False, error_msg
                
        except requests.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"上传过程出错: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
    def get_accounts(self) -> Tuple[bool, List[Dict], str]:
        """
        获取当前激活码下的所有账号
        
        Returns:
            Tuple[bool, List[Dict], str]: (是否成功, 账号列表, 错误信息)
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.auth_token}",
                "Content-Type": "application/json"
            }
            
            logger.info("正在获取账号列表...")
            response = requests.get(
                self.api_url,
                headers=headers,
                timeout=config.api_timeout
            )
            
            if response.status_code == 200:
                response_data = response.json()
                # 从响应中提取accounts数组
                accounts = response_data.get("accounts", [])
                logger.info(f"成功获取 {len(accounts)} 个账号")
                return True, accounts, ""
            else:
                error_msg = response.json().get("message", "获取账号列表失败")
                logger.error(f"获取账号列表失败: {error_msg}")
                return False, [], error_msg
                
        except requests.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
        except Exception as e:
            error_msg = f"获取账号列表过程出错: {str(e)}"
            logger.error(error_msg)
            return False, [], error_msg
    
    def get_checksum(self) -> Tuple[bool, str, str]:
        """
        获取校验和
        
        Returns:
            Tuple[bool, str, str]: (是否成功, 校验和, 错误信息)
        """
        try:
            logger.info("正在获取校验和...")
            response = requests.get(
                self.checksum_url,
                timeout=config.api_timeout
            )
            
            if response.status_code == 200:
                checksum = response.text
                logger.info("成功获取校验和")
                return True, checksum, ""
            else:
                error_msg = "获取校验和失败"
                logger.error(error_msg)
                return False, "", error_msg
                
        except requests.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
        except Exception as e:
            error_msg = f"获取校验和过程出错: {str(e)}"
            logger.error(error_msg)
            return False, "", error_msg
    
    def get_user_info(self, access_token: str) -> Tuple[bool, Dict, str]:
        """
        获取用户信息
        
        Args:
            access_token: 访问令牌
            
        Returns:
            Tuple[bool, Dict, str]: (是否成功, 用户信息, 错误信息)
        """
        try:
            # 获取校验和
            success, checksum, error_msg = self.get_checksum()
            if not success:
                return False, {}, error_msg
            
            # 构建token
            token = f"{access_token},{checksum}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "token": token
            }
            
            logger.info("正在获取用户信息...")
            response = requests.post(
                self.user_info_url,
                json=payload,
                headers=headers,
                timeout=config.api_timeout
            )
            
            if response.status_code == 200:
                user_info = response.json()
                logger.info("成功获取用户信息")
                return True, user_info, ""
            else:
                error_msg = "获取用户信息失败"
                logger.error(error_msg)
                return False, {}, error_msg
                
        except requests.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg
        except Exception as e:
            error_msg = f"获取用户信息过程出错: {str(e)}"
            logger.error(error_msg)
            return False, {}, error_msg 