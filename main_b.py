# main_b.py
import datetime
import logging
import random
import time

import requests
from playwright.sync_api import sync_playwright

import config
from login import create_logged_in_context
from read_link import call_airscript as get_wps_links_func
from search_crawl import goto_search_page, search_and_get_sales
from utils import setup_logging

logger = logging.getLogger(__name__)


def call_wps_action(action, **kwargs):
    """调用 AirScript；成功返回响应 dict，网络异常或云端报错返回 None。"""
    payload = {"Context": {"argv": {"action": action, **kwargs}}}
    headers = {"Content-Type": "application/json", "AirScript-Token": config.AIRSCRIPT_TOKEN}
    try:
        r = requests.post(config.AIRSCRIPT_WEBHOOK_B, json=payload, headers=headers, timeout=60)
        resp = r.json()
    except Exception as e:
        logger.error(f"网络请求异常: {repr(e)}")
        return None
    if resp.get("error"):
        logger.error(f"AirScript [{action}] 报错: {resp['error']}")
        return None
    return resp


def run_stage_b():
    logger.info("========== 阶段 B：更新已有商品销量 ==========")

    # 算日期
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    before_yesterday = today - datetime.timedelta(days=2)
    yesterday_str = f"{yesterday.month}.{yesterday.day}"
    before_str = f"{before_yesterday.month}.{before_yesterday.day}"

    # 读 WPS 链接
    logger.info("1. 正在读取 WPS 链接...")
    links = get_wps_links_func()
    if not links:
        raise RuntimeError("读取 WPS 链接失败，跳过阶段 B")
    logger.info(f"✅ 拿到 {len(links)} 个商品链接")

    # 铺列
    logger.info(f"2. 正在 WPS 新增列 (表头: {yesterday_str})...")
    if not call_wps_action("prepare", yesterdayDate=yesterday_str, beforeYesterdayDate=before_str):
        raise RuntimeError("WPS 新增日期列失败")

    # 启动浏览器抓取
    logger.info("3. 启动浏览器开始抓取...")
    final_data = []
    failed_links = []

    with sync_playwright() as p:
        context = create_logged_in_context(p, config.RAW_COOKIE_PATH)
        page = context.new_page()

        logger.info("正在进入蝉妈妈...")
        page.goto(config.START_URL, timeout=30000)
        page.wait_for_load_state("networkidle")
        goto_search_page(page)

        for i, link in enumerate(links, 1):
            logger.info(f"\n[{i}/{len(links)}] 正在搜索: {link[:40]}...")

            # 设置最多重试 3 次
            max_retries = 3
            success = False
            yesterday_sales = None
            thirty_day = None

            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    logger.info(f"   🔄 第 {attempt} 次重试该链接...")
                    # 重试前多等一会，给净化器/滑块留出处理时间
                    time.sleep(random.uniform(5, 10))

                yesterday_sales, thirty_day = search_and_get_sales(page, link)

                # 如果拿到数据了，视为成功，跳出重试
                if yesterday_sales is not None:
                    success = True
                    break
                else:
                    logger.warning(f"   ⚠️ 第 {attempt} 次抓取失败")

            # 3 次重试全部失败，写占位符保证行号不错位
            if not success:
                logger.error(f"   ❌❌❌ 链接重试 3 次均失败，写入占位符并跳过: {link}")
                failed_links.append(link)
                row_index = 2 * i
                final_data.append({
                    "row": row_index,
                    "yesterdaySales": "获取失败",
                    "thirtyDaySales": "获取失败"
                })
                continue

            row_index = 2 * i
            final_data.append({
                "row": row_index,
                "yesterdaySales": yesterday_sales,
                "thirtyDaySales": thirty_day
            })
            logger.info(f"   ✅ 成功: 昨日销量={yesterday_sales}, 近30日={thirty_day}")

            # 防风控正常延迟
            wait_time = random.uniform(5, 10)
            logger.info(f"   ⏳ 休息 {wait_time:.1f} 秒...")
            time.sleep(wait_time)

            # 每30个商品，强制长休息
            if i % 30 == 0 and i < len(links):
                rest = random.uniform(60, 120)
                logger.info(f"😴 已处理 {i} 个，长休息 {rest:.0f} 秒...")
                time.sleep(rest)

        context.browser.close()

    # 写回 WPS
    if final_data:
        logger.info(f"4. 正在将 {len(final_data)} 条数据写回 WPS...")
        if not call_wps_action("write_data", dataList=final_data):
            raise RuntimeError(f"写回 WPS 失败，{len(final_data)} 条数据未落表")
    else:
        logger.warning("⚠️ 没有抓到任何有效数据，跳过写入。")

    if failed_links:
        logger.warning(f"本次共 {len(failed_links)} 条链接抓取失败（已写占位）：{failed_links}")

    logger.info("✅ 阶段 B 完成！")


if __name__ == "__main__":
    setup_logging()
    run_stage_b()
