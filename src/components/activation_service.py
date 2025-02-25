import json
import requests
from datetime import datetime
from typing import Optional, Dict, Tuple
from src.config import config
from .logger import logger

class ActivationService:
    def __init__(self):
        self.api_url = config.api_url
    
    def activate(self, code: str) -> Tuple[bool, Optional[Dict], str]:
        """
        验证激活码
        
        Args:
            code: 激活码
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (是否成功, 令牌信息, 错误信息)
        """
        try:
            # 准备请求数据
            payload = {
                "code": code
            }
            
            # 发送激活请求
            response = requests.post(
                self.api_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=config.api_timeout
            )
            
            # 检查响应状态
            if response.status_code == 200:
                data = response.json()
                logger.info(f"激活成功，过期时间: {data.get('expires_at')}")
                return True, data, ""
            else:
                error_msg = response.json().get("message", "激活失败")
                logger.error(f"激活失败: {error_msg}")
                return False, None, error_msg
                
        except requests.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except json.JSONDecodeError as e:
            error_msg = f"响应格式错误: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"激活过程出错: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
            
    def get_code_info(self, code: str = "") -> Tuple[bool, Optional[Dict], str]:
        """
        获取激活码信息
        
        Args:
            code: 激活码，如果为空则使用当前的auth_token获取信息
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (是否成功, 激活码信息, 错误信息)
        """
        try:
            # 准备请求URL
            code_info_url = f"{config.api_base_url}{config.code_info_endpoint}"
            
            # 准备请求头信息
            headers = {"Content-Type": "application/json"}
            
            # 如果有auth_token，添加到请求头
            if config.auth_token:
                headers["Authorization"] = f"Bearer {config.auth_token}"
            
            # 准备查询参数
            params = {}
            if code:
                params["code"] = code
            
            logger.info(f"发送GET请求到: {code_info_url}")
            
            # 发送获取激活码信息请求 - 使用GET方法
            response = requests.get(
                code_info_url,
                params=params,
                headers=headers,
                timeout=config.api_timeout
            )
            
            # 记录响应状态和内容
            logger.info(f"响应状态码: {response.status_code}")
            logger.info(f"响应内容: {response.text[:100]}...")
            
            # 检查响应状态
            if response.status_code == 200:
                try:
                    data = response.json()
                    logger.info(f"获取激活码信息成功: {data}")
                    return True, data, ""
                except json.JSONDecodeError as e:
                    # 尝试手动解析JSON
                    text = response.text.strip()
                    if text.startswith('{') and text.endswith('}'):
                        try:
                            # 可能有额外的字符，尝试清理并解析
                            cleaned_text = text[text.find('{'):text.rfind('}')+1]
                            data = json.loads(cleaned_text)
                            logger.info(f"手动解析JSON成功: {data}")
                            return True, data, ""
                        except json.JSONDecodeError:
                            error_msg = f"响应格式错误，无法解析JSON: {text}"
                            logger.error(error_msg)
                            return False, None, error_msg
                    else:
                        error_msg = f"响应不是有效的JSON格式: {text}"
                        logger.error(error_msg)
                        return False, None, error_msg
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("message", "获取激活码信息失败")
                except:
                    error_msg = f"获取激活码信息失败，状态码: {response.status_code}"
                
                logger.error(f"获取激活码信息失败: {error_msg}")
                return False, None, error_msg
                
        except requests.RequestException as e:
            error_msg = f"网络请求错误: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except json.JSONDecodeError as e:
            error_msg = f"响应格式错误: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg
        except Exception as e:
            error_msg = f"获取激活码信息过程出错: {str(e)}"
            logger.error(error_msg)
            return False, None, error_msg 