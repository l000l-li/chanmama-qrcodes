# crawl.py
import logging
import re

from utils import handle_slider_if_present, human_delay

logger = logging.getLogger(__name__)


def run_business_action(page):
    """进入商品列表页"""
    page.locator("#menu-box-out").get_by_text("商品", exact=True).click()
    human_delay(1, 2)
    page.locator("#menu-box-out").get_by_role("link").filter(
        has_text=re.compile(r"^$")
    ).first.click()
    human_delay(1, 2)
    page.locator("div").filter(
        has_text=re.compile(r"^快捷操作鞋子重命名删除$")
    ).locator("span").click()
    human_delay(1, 3)
    logger.info("✅ 已执行：商品菜单 -> 链接 -> 快捷操作")


def collect_product_hrefs(page):
    """收集当前页所有商品链接的 href"""
    links = page.locator('a[href*="/promotionRank/"][href$=".html"]').filter(
        has_text=re.compile(r"\S")
    )
    count = links.count()
    logger.info(f"原始商品链接数量: {count}")

    hrefs, seen = [], set()
    for i in range(count):
        h = links.nth(i).get_attribute("href")
        if h and h not in seen:
            seen.add(h)
            hrefs.append(h)
    logger.info(f"去重后商品数量: {len(hrefs)}")
    return hrefs


def click_next_page(page):
    """点"下一页"按钮，返回 True=成功翻页，False=最后一页/没按钮"""
    try:
        next_btn = page.locator("button.btn-next").first
        if next_btn.count() == 0:
            return False

        disabled = next_btn.get_attribute("disabled")
        if disabled is not None:
            return False

        next_btn.click()
        human_delay(2, 4)
        page.wait_for_load_state("domcontentloaded")

        # ← 翻页后，检查滑块（会先等 2 秒）
        handle_slider_if_present(page)

        return True

    except Exception as e:
        logger.warning(f"   翻页失败: {repr(e)}")
        return False
