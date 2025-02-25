import time
import re
import random
import string
from TempMail import TempMail
from src.components.logger import logger

class EmailVerificationHandlerTemp:
    def __init__(self, max_retries=10, retry_interval=5):
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.tmp = TempMail("optional-api-key")
        self.email_address = None
        self.email_token = None
        self.email_password = None  # 添加密码存储

    async def generate_random_email(self):
        """
        生成随机邮箱账号
        Returns:
            tuple: (email_address, token, password)
        """
        try:
            # 生成随机用户名
            random_username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            
            # 创建邮箱账号
            logger.info("正在创建临时邮箱...")
            inb = self.tmp.createInbox(prefix=random_username)
            # inb格式: Inbox (address=joe16869@cf4r.awesome47.com, token=2x8nscbuaulnu5kh3t5rjlhkaym3uddmss8fm1)
            
            # 解析邮箱地址和token
            self.email_address = inb.address
            self.email_token = inb.token
            self.email_password = inb.token
            
            logger.info(f"临时邮箱创建成功: {self.email_address}")
            return self.email_address, self.email_token, self.email_password
            
        except Exception as e:
            logger.error(f"生成随机邮箱失败: {str(e)}")
            return None, None, None

    async def get_verification_code(self):
        """
        获取验证码，支持多次重试
        Returns:
            str: 验证码，如果获取失败返回 None
        """
        if not self.email_token:
            logger.error("未找到邮箱token，请先调用 generate_random_email()")
            return None
            
        verify_code = None
        
        try:
            logger.info("正在等待并获取验证码...")
            
            # 尝试指定次数
            for attempt in range(self.max_retries):
                try:
                    # 获取邮件内容
                    emails = self.tmp.getEmails(self.email_token)
                    
                    if emails and len(emails) > 0:
                        # 获取最新邮件
                        latest_email = emails[0]
                        logger.debug(f"收到新邮件")
                        
                        # 提取邮件内容
                        message_text = str(latest_email)
                        
                        # 提取验证码 - 在 "Enter the code below in your open browser window." 之后的6位数字
                        code_match = re.search(r'Enter the code below in your open browser window\.\s*\n\s*(\d{6})', message_text)
                        if code_match:
                            verify_code = code_match.group(1)
                            logger.info(f"成功获取验证码: {verify_code}")
                            break
                    
                    if attempt < self.max_retries - 1:
                        logger.info(f"第 {attempt + 1} 次尝试未获取到验证码，{self.retry_interval} 秒后重试...")
                        time.sleep(self.retry_interval)
                    else:
                        logger.error("验证码获取失败，已达到最大重试次数")
                
                except Exception as e:
                    logger.error(f"获取邮件时发生错误: {str(e)}")
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_interval)
                    
        except Exception as e:
            logger.error(f"验证码获取过程发生异常: {str(e)}")
            
        return verify_code

    async def _cleanup_mail(self, message_id):
        """
        删除指定ID的邮件 (TempMail库可能不支持此功能，保留此方法以保持接口一致)
        """
        try:
            # TempMail库可能不支持删除邮件，这里只是占位
            return True
        except Exception as e:
            logger.error(f"删除邮件失败: {str(e)}")
            return False


if __name__ == "__main__":
    # 测试新的验证码获取类
    import asyncio
    
    async def test_temp_handler():
        handler = EmailVerificationHandlerTemp()
        
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
    
    asyncio.run(test_temp_handler())



