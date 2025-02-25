import os
import sys

from DrissionPage import ChromiumOptions, Chromium
from dotenv import load_dotenv
from .logger import logger  # 导入项目的 logger

load_dotenv()


class BrowserManager:
    def __init__(self):
        self.browser = None

    def init_browser(self, user_agent=None):
        """初始化浏览器"""
        co = self._get_browser_options(user_agent)
        self.browser = Chromium(co)
        return self.browser

    def _get_browser_options(self, user_agent=None):
        """获取浏览器配置"""
        co = ChromiumOptions()
        try:
            extension_path = self._get_extension_path()
            co.add_extension(extension_path)
        except FileNotFoundError as e:
            logger.warning(f"警告: {e}")  # 使用 logger 替换 logging

        co.set_pref("credentials_enable_service", False)
        co.set_argument("--hide-crash-restore-bubble")
        proxy = os.getenv("BROWSER_PROXY")
        if proxy:
            co.set_proxy(proxy)
            logger.info(f"使用代理: {proxy}")  # 添加代理信息日志

        co.auto_port()
        if user_agent:
            co.set_user_agent(user_agent)
            logger.info(f"设置 User-Agent: {user_agent}")  # 添加 user-agent 信息日志

        headless = os.getenv("BROWSER_HEADLESS", "True").lower() == "true"
        co.headless(headless)
        logger.info(f"无头模式: {headless}")  # 添加无头模式信息日志

        # Mac 系统特殊处理
        if sys.platform == "darwin":
            co.set_argument("--no-sandbox")
            co.set_argument("--disable-gpu")
            logger.info("已应用 macOS 特殊配置")  # 添加系统配置信息日志

        return co

    def _get_extension_path(self):
        """获取插件路径"""
        if getattr(sys, '_MEIPASS', None):
            # 打包环境
            extension_path = os.path.join(sys._MEIPASS, "turnstilePatch")
            logger.info("使用打包环境插件路径")  # 添加环境信息日志
        else:
            # 开发环境
            extension_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "turnstilePatch")
            logger.info("使用开发环境插件路径")  # 添加环境信息日志

        if not os.path.exists(extension_path):
            error_msg = f"插件不存在: {extension_path}"
            logger.error(error_msg)  # 添加错误日志
            raise FileNotFoundError(error_msg)

        logger.info(f"插件路径: {extension_path}")  # 添加路径信息日志
        return extension_path

    def quit(self):
        """关闭浏览器"""
        if self.browser:
            try:
                self.browser.quit()
                logger.info("浏览器已关闭")  # 添加关闭信息日志
            except Exception as e:
                logger.error(f"关闭浏览器时出错: {str(e)}")  # 添加错误日志
                pass
