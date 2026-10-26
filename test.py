# test.py
import logging

from playwright.sync_api import sync_playwright

import config
from login import create_logged_in_context
from search_crawl import goto_search_page, search_and_get_sales
from utils import setup_logging

logger = logging.getLogger(__name__)


def main():
    # 拿一个真实的链接来测（你之前 WPS 读出来的第一个）
    test_link = "https://haohuo.jinritemai.com/ecommerce/trade/detail/index.html?id=3819636350731289010&ins_activity_param=pl7O-g_mRlw&origin_type=pc_buyin_group&pick_source=v.pLUbMo"

    with sync_playwright() as p:
        # 1. 启动浏览器并带上登录态
        context = create_logged_in_context(p, config.RAW_COOKIE_PATH)
        page = context.new_page()

        # 2. 打开蝉妈妈首页
        logger.info("正在打开蝉妈妈...")
        page.goto(config.START_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        logger.info("✅ 页面打开完毕")

        # 3. 进入搜索页（复用 search_crawl.py）
        goto_search_page(page)

        # 4. 搜索单个链接（复用 search_crawl.py）
        logger.info(f"\n开始测试搜索链接: {test_link}")
        yesterday, thirty = search_and_get_sales(page, test_link)

        logger.info("========== 测试结果 ==========")
        logger.info(f"昨日销量: {yesterday}")
        logger.info(f"近30日销量: {thirty}")
        logger.info("==============================")

        input("\n测试完毕，回车关闭浏览器...")
        context.browser.close()


if __name__ == "__main__":
    setup_logging()
    main()
