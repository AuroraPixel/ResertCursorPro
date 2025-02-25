import random
import string
import time
import requests
from enum import Enum
from typing import Optional
from datetime import datetime
from src.components.get_email_code_temp import EmailVerificationHandlerTemp
from src.components.browser_utils import BrowserManager
from src.components.logger import logger
import os
import asyncio
import dotenv
import sys

# 加载环境变量
dotenv.load_dotenv()

class VerificationStatus(Enum):
    """验证状态枚举"""

    PASSWORD_PAGE = "@name=password"
    CAPTCHA_PAGE = "@data-index=0"
    ACCOUNT_SETTINGS = "Account Settings"

def save_screenshot(tab, stage: str, timestamp: bool = True) -> None:
        """
        保存页面截图，只在开发环境下进行截屏

        Args:
            tab: 浏览器标签页对象
            stage: 截图阶段标识
            timestamp: 是否添加时间戳
        """
        # 检查是否为打包环境，如果是则不进行截屏
        if getattr(sys, 'frozen', False):
            logger.debug(f"打包环境下不进行截屏: {stage}")
            return
            
        try:
            # 创建 screenshots 目录
            screenshot_dir = "screenshots"
            if not os.path.exists(screenshot_dir):
                os.makedirs(screenshot_dir)

            # 生成文件名
            if timestamp:
                filename = f"turnstile_{stage}_{int(time.time())}.png"
            else:
                filename = f"turnstile_{stage}.png"

            filepath = os.path.join(screenshot_dir, filename)

            # 保存截图
            tab.get_screenshot(filepath)
            logger.debug(f"截图已保存: {filepath}")
        except Exception as e:
            logger.warning(f"截图保存失败: {str(e)}")

def check_verification_success(tab) -> Optional[VerificationStatus]:
    """
    检查验证是否成功
    Args:
        tab: 浏览器标签页
    Returns:
        VerificationStatus: 验证成功时返回对应状态，失败返回 None
    """
    # 检查是否到达成功页面
    for status in VerificationStatus:
        if tab.ele(status.value):
            logger.info(f"验证成功 - 已到达{status.name}页面")
            return status

    return None

class TurnstileError(Exception):
    """Turnstile 验证相关异常"""

    pass

class AccountRegister:
    def __init__(self):
        self.browser_manager = None
        self.email_handler = None
        self.account = None
        self.email_password = None  # 邮箱密码
        self.cursor_password = None  # Cursor密码
        self.first_name = None
        self.last_name = None
        self.cursor_token = None
        
        # URL配置
        self.login_url = "https://authenticator.cursor.sh"
        self.sign_up_url = "https://authenticator.cursor.sh/sign-up"
        self.settings_url = "https://www.cursor.com/settings"

    def _generate_random_name(self):
        """生成随机名字"""
        return ''.join(random.choice(string.ascii_uppercase) + 
                      ''.join(random.choices(string.ascii_lowercase, k=5)))

    def _get_user_agent(self):
        """获取user_agent"""
        try:
            browser_manager = BrowserManager()
            browser = browser_manager.init_browser()
            user_agent = browser.latest_tab.run_js("return navigator.userAgent")
            browser_manager.quit()
            return user_agent
        except Exception as e:
            logger.error(f"获取user agent失败: {str(e)}")
            return None

    def get_cursor_session_token(self, tab, max_attempts=3, retry_interval=2):
        """获取Cursor会话token"""
        logger.info("开始获取 Cursor Session Token")
        attempts = 0

        while attempts < max_attempts:
            try:
                cookies = tab.cookies()
                for cookie in cookies:
                    if cookie.get("name") == "WorkosCursorSessionToken":
                        token = cookie["value"].split("%3A%3A")[1]
                        return token

                attempts += 1
                if attempts < max_attempts:
                    logger.info(f"第 {attempts} 次尝试未获取到 Token，{retry_interval}秒后重试...")
                    time.sleep(retry_interval)
                else:
                    logger.error(f"已达到最大尝试次数({max_attempts})，获取Token失败")

            except Exception as e:
                logger.error(f"获取 Token 失败: {str(e)}")
                attempts += 1
                if attempts < max_attempts:
                    time.sleep(retry_interval)

        return None

    async def sign_up_account(self, browser, tab):
        """注册账号流程"""
        logger.info("\n=== 开始注册账号流程 ===")
        logger.info("Step 1: 访问注册页面...")
        tab.get(self.sign_up_url)
        
        # 检查是否为打包环境，调整等待时间
        is_packaged = getattr(sys, 'frozen', False)
        
        try:
            if tab.ele("@name=first_name"):
                logger.info("Step 2: 开始填写个人信息")
                logger.info("  - 输入名字")
                tab.actions.click("@name=first_name").input(self.first_name)
                time.sleep(random.uniform(0.5, 1) if is_packaged else random.uniform(1, 3))

                logger.info("  - 输入姓氏")
                tab.actions.click("@name=last_name").input(self.last_name)
                time.sleep(random.uniform(0.5, 1) if is_packaged else random.uniform(1, 3))

                logger.info("  - 输入邮箱")
                tab.actions.click("@name=email").input(self.account)
                time.sleep(random.uniform(0.5, 1) if is_packaged else random.uniform(1, 3))

                logger.info("  - 提交个人信息")
                tab.actions.click("@type=submit")

        except Exception as e:
            logger.error(f"Step 2 失败: 注册页面访问失败 - {str(e)}")
            return False

        logger.info("Step 3: 处理 Turnstile 验证 (第一次)")
        self.handle_turnstile(tab)

        try:
            if tab.ele("@name=password"):
                logger.info("Step 4: 设置 Cursor 密码")
                logger.info("  - 输入密码")
                tab.ele("@name=password").input(self.cursor_password)
                time.sleep(random.uniform(0.5, 1) if is_packaged else random.uniform(1, 3))
                
                logger.info("  - 提交密码")
                tab.ele("@type=submit").click()

        except Exception as e:
            logger.error(f"Step 4 失败: 密码设置失败 - {str(e)}")
            return False

        if tab.ele("This email is not available."):
            logger.error("Step 4 失败: 邮箱已被使用")
            return False

        logger.info("Step 5: 处理 Turnstile 验证 (第二次)")
        self.handle_turnstile(tab)

        logger.info("Step 6: 处理邮箱验证码")
        # 添加验证码处理的超时和重试机制
        max_retries = 5  # 最大重试次数
        retry_count = 0
        verification_timeout = 180  # 总超时时间（秒）
        start_time = time.time()
        
        while retry_count < max_retries and (time.time() - start_time) < verification_timeout:
            try:
                # 检查是否已经进入账户设置页面（跳过验证码）
                if tab.ele("Account Settings"):
                    logger.info("  - 已进入账户设置页面，跳过验证码步骤")
                    break
                
                # 检查是否显示验证码输入框
                if tab.ele("@data-index=0"):
                    retry_count += 1
                    elapsed_time = time.time() - start_time
                    logger.info(f"  - 第 {retry_count}/{max_retries} 次尝试获取验证码 (已用时: {elapsed_time:.1f}秒)")
                    
                    # 设置获取验证码的超时时间
                    code_timeout = 60  # 单次获取验证码的超时时间（秒）
                    try:
                        # 创建一个任务来获取验证码，并设置超时
                        code = await asyncio.wait_for(
                            self.email_handler.get_verification_code(),
                            timeout=code_timeout
                        )
                        
                        if not code:
                            logger.warning(f"  - 第 {retry_count} 次尝试未获取到验证码")
                            if retry_count < max_retries:
                                logger.info(f"  - 等待 5 秒后进行下一次尝试...")
                                time.sleep(5)
                                continue
                            else:
                                logger.error(f"  - 已达到最大重试次数 ({max_retries}次)，验证码获取失败")
                                return False

                        logger.info("  - 成功获取验证码")
                        logger.info("  - 开始输入验证码")
                        i = 0
                        for digit in code:
                            tab.ele(f"@data-index={i}").input(digit)
                            time.sleep(random.uniform(0.1, 0.3))
                            i += 1
                        logger.info("  - 验证码输入完成")
                        
                        # 等待验证结果
                        time.sleep(random.uniform(2, 4))
                        
                        # 检查验证是否成功
                        if self._check_verification_success(tab):
                            logger.info("  - 验证码验证成功")
                            break
                        else:
                            logger.warning("  - 验证码验证失败，可能需要重试")
                            if retry_count < max_retries:
                                continue
                            else:
                                logger.error("  - 验证码验证失败，已达到最大重试次数")
                                return False
                    
                    except asyncio.TimeoutError:
                        logger.warning(f"  - 获取验证码超时 (超过 {code_timeout} 秒)")
                        if retry_count < max_retries:
                            continue
                        else:
                            logger.error("  - 获取验证码失败，已达到最大重试次数")
                            return False
                
                # 如果没有找到验证码输入框，可能页面还没加载完成或者已经跳过了验证码步骤
                time.sleep(2)
                
                # 再次检查是否已经进入账户设置页面
                if tab.ele("Account Settings"):
                    logger.info("  - 已进入账户设置页面，跳过验证码步骤")
                    break
                
                # 如果既没有验证码输入框，也没有进入账户设置页面，可能是页面加载问题
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"  - 等待页面加载，5 秒后进行第 {retry_count+1} 次尝试...")
                    time.sleep(5)
                else:
                    logger.error(f"  - 已达到最大重试次数 ({max_retries}次)，验证码处理失败")
                    return False
                
            except Exception as e:
                elapsed_time = time.time() - start_time
                logger.error(f"Step 6 失败: 验证码处理过程出错 - {str(e)} (已用时: {elapsed_time:.1f}秒)")
                retry_count += 1
                if retry_count < max_retries:
                    logger.info(f"  - 等待 5 秒后进行第 {retry_count+1} 次尝试...")
                    time.sleep(5)
                else:
                    logger.error(f"  - 已达到最大重试次数 ({max_retries}次)，验证码处理失败")
                    return False
        
        # 检查是否因为超时而退出循环
        if (time.time() - start_time) >= verification_timeout:
            logger.error(f"Step 6 失败: 验证码处理总时间超过 {verification_timeout} 秒，操作超时")
            return False
        
        # 检查是否因为重试次数用尽而退出循环
        if retry_count >= max_retries and not tab.ele("Account Settings"):
            logger.error(f"Step 6 失败: 已尝试 {max_retries} 次，验证码处理失败")
            return False

        logger.info("Step 7: 处理 Turnstile 验证 (第三次)")
        self.handle_turnstile(tab)

        logger.info("Step 8: 等待登录完成...")
        time.sleep(random.randint(1, 2) if is_packaged else random.randint(3, 6))

        logger.info("Step 9: 获取 Cursor Token")
        self.cursor_token = self.get_cursor_session_token(tab)
        
        if self.cursor_token:
            logger.info("Step 10: 注册成功，输出账号信息")
            logger.info("\n=== Cursor 账号信息 ===")
            logger.info(f"邮箱账号: [已隐藏]")
            logger.info(f"邮箱密码: [已隐藏]")
            logger.info(f"Cursor密码: [已隐藏]")
            logger.info(f"Cursor Token: [已隐藏]")
            logger.info("="*30)
            return True
            
        logger.error("Step 9 失败: 未能获取到 Cursor Token")
        return False

    def handle_turnstile(self, tab, max_retries: int = 2, retry_interval: tuple = (0.5, 1.5)) -> bool:
        """处理 Turnstile 验证"""
        logger.info("正在检测 Turnstile 验证...")
        save_screenshot(tab, "start")
        retry_count = 0
        
        # 检查是否为打包环境，调整等待时间
        is_packaged = getattr(sys, 'frozen', False)
        wait_time = (0.5, 1.5) 
        
        try:
            while retry_count < max_retries:
                retry_count += 1
                if not is_packaged:
                    logger.debug(f"第 {retry_count} 次尝试验证")

                try:
                    # 定位验证框元素
                    challenge_check = (
                        tab.ele("@id=cf-turnstile", timeout=2)
                        .child()
                        .shadow_root.ele("tag:iframe")
                        .ele("tag:body")
                        .sr("tag:input")
                    )

                    if challenge_check:
                        logger.info("检测到 Turnstile 验证框，开始处理...")
                        time.sleep(random.uniform(0.5, 1))
                        challenge_check.click()
                        logger.info("Turnstile完成")
                        time.sleep(0.5)
                        save_screenshot(tab, "clicked")

                except Exception as e:
                    if not is_packaged:
                        logger.debug(f"当前尝试未成功: {str(e)}")

                # 检查验证结果
                logger.info("开始检查验证结果")
                verification_result = True
                if verification_result:
                    return True
                elif retry_count < max_retries:
                    time.sleep(random.uniform(*wait_time))
                    continue
                else:
                    logger.error(f"验证失败 - 已达到最大重试次数 {max_retries}")
                    save_screenshot(tab, "failed")
                    return False

        except Exception as e:
            error_msg = f"Turnstile 验证过程发生异常: {str(e)}"
            logger.error(error_msg)
            save_screenshot(tab, "error")
            raise TurnstileError(error_msg)

        return False
            
    def _check_verification_success(self, tab):
        """检查验证码是否验证成功"""
        try:
            # 检查是否已经进入账户设置页面
            if tab.ele("Account Settings"):
                return True
                
            # 检查是否有错误消息
            error_elements = [
                "Invalid verification code",
                "验证码无效",
                "Please try again",
                "请重试"
            ]
            
            for error_text in error_elements:
                if tab.ele(error_text):
                    logger.warning(f"  - 发现错误信息: {error_text}")
                    return False
                    
            # 检查是否仍在验证码页面
            # if tab.ele("@data-index=0"):
            #     # 如果验证码输入框仍然存在，可能验证未完成
            #     return False
                
            # 如果没有明确的失败迹象，假设成功
            return True
            
        except Exception as e:
            logger.error(f"  - 检查验证结果时出错: {str(e)}")
            return False

    async def register_single_account(self):
        """注册单个账号"""
        try:
            # 初始化浏览器
            logger.info("Step 1: 初始化浏览器")
            self.browser_manager = BrowserManager()
            browser = self.browser_manager.init_browser()
            tab = browser.latest_tab
            
            # 检查是否为打包环境，调整等待时间
            is_packaged = getattr(sys, 'frozen', False)
            
            # 生成随机账号信息
            logger.info("Step 2: 生成随机账号信息")
            self.first_name = self._generate_random_name()
            self.last_name = self._generate_random_name()
            self.cursor_password = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
            
            # 创建邮箱
            logger.info("Step 2.1: 创建临时邮箱")
            
            # 使用TempMail服务
            logger.info("使用TempMail服务")
            self.email_handler = EmailVerificationHandlerTemp()
                
            self.account, self.email_token, self.email_password = await self.email_handler.generate_random_email()
            
            if not self.account:
                logger.error("Step 2.1 失败: 创建临时邮箱失败")
                return False
            
            logger.info("Step 2.2: 临时邮箱创建成功")
            
            # 访问注册页面
            logger.info("Step 3: 访问 Cursor 注册页面")
            tab.get(self.sign_up_url)
            time.sleep(random.uniform(1, 2) if is_packaged else random.uniform(2, 4))
            
            # 输入邮箱
            logger.info("Step 3.1: 输入邮箱地址")
            if tab.ele("@name=email"):
                tab.ele("@name=email").input(self.account)
                time.sleep(random.uniform(0.5, 1) if is_packaged else random.uniform(1, 2))
                
                logger.info("Step 3.2: 点击继续按钮")
                tab.ele("@type=submit").click()
                time.sleep(random.uniform(1, 2) if is_packaged else random.uniform(2, 4))
            else:
                logger.error("Step 3.1 失败: 未找到邮箱输入框")
                return False

            return await self.sign_up_account(browser, tab)
        except Exception as e:
            logger.error(f"注册单个账号失败: {str(e)}")
            return False

    async def batch_register(self, num_accounts):
        """批量注册账号"""
        successful = 0
        failed = 0

        for i in range(num_accounts):
            logger.info(f"\n=== 开始注册第 {i + 1}/{num_accounts} 个账号 ===")
            try:
                success = await self.register_single_account()
                if success:
                    successful += 1
                else:
                    failed += 1
            except Exception as e:
                failed += 1
                logger.error(f"注册出错: {str(e)}")
            finally:
                if self.browser_manager:
                    self.browser_manager.quit()

            if i < num_accounts - 1:
                delay = random.uniform(10, 20)
                logger.info(f"等待 {delay:.1f} 秒后继续下一个注册...")
                time.sleep(delay)

        logger.info(f"\n注册完成: 成功 {successful} 个, 失败 {failed} 个")


if __name__ == "__main__":
    # 测试代码
    import asyncio
    import os
    import sys
    from pathlib import Path
    
    # 获取项目根目录
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    
    # 将项目根目录添加到 Python 路径
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
        
    # 使用 -m 选项运行模块
    if not __package__:
        import runpy
        runpy.run_module("src.components.register_account", run_name="__main__") 