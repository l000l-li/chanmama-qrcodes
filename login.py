# login.py
import json
import logging
import os

import config

logger = logging.getLogger(__name__)


def create_logged_in_context(p, cookie_path):
    """返回一个已登录的浏览器上下文，并自带反检测"""
    if not os.path.exists(cookie_path):
        raise FileNotFoundError(f"找不到 cookie 文件：{cookie_path}，请重新导出登录态")

    with open(cookie_path, "r", encoding="utf-8") as f:
        storage_data = json.load(f)

    logger.info(f"启动浏览器（headless={config.HEADLESS}, slow_mo={config.SLOW_MO}）")
    browser = p.chromium.launch(
        headless=config.HEADLESS,
        slow_mo=config.SLOW_MO,
        args=["--disable-blink-features=AutomationControlled"]
    )

    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        storage_state={"cookies": storage_data, "origins": []},
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
    )

    # 直接注入反检测脚本，完美解决 webdriver 检测
    context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        Object.defineProperty(navigator, 'languages', {get: () => ['zh-CN', 'zh']});
        Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
        window.chrome = { runtime: {} };
    """)

    return context
