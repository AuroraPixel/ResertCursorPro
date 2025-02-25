import time
import re
import requests
import random
import string

class EmailVerificationHandlerNew:
    def __init__(self, max_retries=10, retry_interval=5):
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.session = requests.Session()
        self.email_address = None
        self.email_token = None
        self.email_password = None  # 添加密码存储
        self.BASE_URL = "https://api.mail.tm"

    async def generate_random_email(self):
        """
        生成随机邮箱账号
        Returns:
            tuple: (email_address, token, password)
        """
        try:
            # 获取可用域名
            response = requests.get(f"{self.BASE_URL}/domains")
            if response.status_code != 200:
                raise Exception("无法获取邮箱域名列表")
            
            domains = response.json()
            if not domains.get('hydra:member'):
                raise Exception("没有可用的邮箱域名")
            
            domain = domains['hydra:member'][0]['domain']
            
            # 生成随机用户名
            random_username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            email = f"{random_username}@{domain}"
            
            # 生成随机密码
            password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            # 创建邮箱账号
            account_data = {
                "address": email,
                "password": password
            }
            
            response = requests.post(
                f"{self.BASE_URL}/accounts",
                json=account_data
            )
            
            if response.status_code != 201:
                raise Exception("创建邮箱账号失败")
            
            # 获取token
            response = requests.post(
                f"{self.BASE_URL}/token",
                json=account_data
            )
            
            if response.status_code != 200:
                raise Exception("获取邮箱token失败")
            
            self.email_address = email
            self.email_token = response.json()['token']
            self.email_password = password
            
            print("成功创建临时邮箱")
            return email, self.email_token, password
            
        except Exception as e:
            print(f"生成随机邮箱失败: {str(e)}")
            return None, None, None

    async def get_verification_code(self):
        """
        获取验证码，支持多次重试
        Returns:
            str: 验证码，如果获取失败返回 None
        """
        if not self.email_token:
            print("未找到邮箱token，请先调用 generate_random_email()")
            return None
            
        verify_code = None
        
        try:
            print("正在等待并获取验证码...")
            
            # 尝试指定次数
            for attempt in range(self.max_retries):
                try:
                    # 获取邮件内容
                    response = requests.get(
                        f"{self.BASE_URL}/messages",
                        headers={
                            'Authorization': f'Bearer {self.email_token}',
                            'Content-Type': 'application/json'
                        }
                    )
                    
                    if response.status_code == 200:
                        messages = response.json()
                        if messages.get('hydra:member'):
                            # 获取最新邮件
                            latest_message = messages['hydra:member'][0]
                            
                            # 下载邮件内容
                            message_response = requests.get(
                                f"{self.BASE_URL}{latest_message['downloadUrl']}",
                                headers={'Authorization': f'Bearer {self.email_token}'}
                            )
                            
                            if message_response.status_code == 200:
                                message_text = message_response.text
                                
                                # 提取验证码 - 在 "Enter the code below in your open browser window." 之后的6位数字
                                code_match = re.search(r'Enter the code below in your open browser window\.\s*\n\s*(\d{6})', message_text)
                                if code_match:
                                    verify_code = code_match.group(1)
                                    print(f"成功获取验证码: {verify_code}")
                                    
                                    # 删除已读邮件
                                    await self._cleanup_mail(latest_message['id'])
                                    break
                    
                    if attempt < self.max_retries - 1:
                        print(f"第 {attempt + 1} 次尝试未获取到验证码，{self.retry_interval} 秒后重试...")
                        time.sleep(self.retry_interval)
                    else:
                        print("验证码获取失败，已达到最大重试次数")
                
                except Exception as e:
                    print(f"获取邮件时发生错误: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_interval)
                    
        except Exception as e:
            print(f"验证码获取过程发生异常: {str(e)}")
            
        return verify_code

    async def _cleanup_mail(self, message_id):
        """
        删除指定ID的邮件
        """
        try:
            response = requests.delete(
                f"{self.BASE_URL}/messages/{message_id}",
                headers={'Authorization': f'Bearer {self.email_token}'}
            )
            return response.status_code == 204
        except Exception as e:
            print(f"删除邮件失败: {str(e)}")
            return False


if __name__ == "__main__":
    # 测试新的验证码获取类
    import asyncio
    
    async def test_new_handler():
        handler = EmailVerificationHandlerNew()
        
        # 首先生成随机邮箱
        email, token, password = await handler.generate_random_email()
        if email and token:
            print(f"生成的邮箱: {email}")
            print(f"密码: {password}")
            print(f"Token: {token}")
            
            # 获取验证码
            code = await handler.get_verification_code()
            print(f"获取到的验证码: {code}")
        else:
            print("邮箱生成失败")
    
    asyncio.run(test_new_handler())
