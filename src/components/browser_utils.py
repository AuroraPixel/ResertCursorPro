import os
import sys

from DrissionPage import ChromiumOptions, Chromium
from dotenv import load_dotenv
from .logger import logger  # 导入项目的 logger

# 确保每次都重新加载环境变量
load_dotenv(override=True)


class BrowserManager:
    def __init__(self):
        self.browser = None

    def init_browser(self, user_agent=None):
        """初始化浏览器"""
        co = self._get_browser_options(user_agent)
        logger.info("正在初始化浏览器...")
        self.browser = Chromium(co)
        logger.info("浏览器初始化完成")
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
        
        # 添加窗口大小设置
        co.set_argument("--window-size=1280,800")
        logger.info("设置浏览器窗口大小: 1280x800")
        
        proxy = os.getenv("BROWSER_PROXY")
        if proxy:
            co.set_proxy(proxy)
            logger.info(f"使用代理: {proxy}")  # 添加代理信息日志

        co.auto_port()
        if user_agent:
            co.set_user_agent(user_agent)
            logger.info(f"设置 User-Agent: {user_agent}")  # 添加 user-agent 信息日志

        # 根据环境决定是否使用无头模式
        # 在打包环境中默认使用无头模式，在开发环境中根据环境变量决定
        is_packaged = getattr(sys, 'frozen', False)
        
        if is_packaged:
            # 打包环境强制使用无头模式
            headless = True
            logger.info("打包环境: 强制使用无头模式")
        else:
            # 开发环境根据环境变量决定
            headless_env = os.getenv("BROWSER_HEADLESS", "False").lower()
            headless = headless_env == "true"
            logger.info(f"开发环境: 无头模式设置为 {headless} (环境变量值: {headless_env})")
        
        co.headless(headless)

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
