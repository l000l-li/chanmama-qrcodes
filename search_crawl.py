# search_crawl.py
import logging
import random
import re

from utils import clean_page_interference, human_delay

logger = logging.getLogger(__name__)


def goto_search_page(page):
    """进入蝉妈妈的商品搜索页"""
    page.locator("#menu-box-out").get_by_text("商品", exact=True).click()
    human_delay(1, 2)
    page.locator("#menu-box-out").get_by_role("link").filter(
        has_text=re.compile(r"^$")
    ).first.click()
    human_delay(2, 4)
    logger.info("✅ 已进入商品搜索页")


def search_and_get_sales(page, link):
    """
    搜索单个商品链接，返回 (昨日销量, 近30日销量)。
    失败返回 (None, None)
    """
    detail = None
    try:
        search_input = page.get_by_placeholder("请输入商品链接、标题或者关键词")
        search_btn = page.locator("#e2e-common-search-btn")

        # 1. 输入前，强制净化页面
        clean_page_interference(page)

        # 2. 输入链接并搜索
        search_input.fill("")
        human_delay(0.5, 1)
        search_input.fill(link)
        human_delay(0.5, 1)
        search_btn.click()

        logger.info("   点击搜索，等待页面响应...")
        # 3. 点完搜索后，强行等 3 秒，然后净化（大概率这里出滑块）
        page.wait_for_timeout(3000)
        clean_page_interference(page)

        # 4. 等待搜索结果加载
        logger.info("   等待搜索结果...")
        product_link_locator = page.locator('a[href*="/promotionRank/"]').filter(
            has_text=re.compile(r"[\u4e00-\u9fa5]")
        ).first

        try:
            product_link_locator.wait_for(state="visible", timeout=10000)
        except Exception:
            # === 兜底：如果 10 秒没出来，说明被拦截了 ===
            logger.warning("   等待结果超时，再次强行净化页面...")
            clean_page_interference(page)
            # 净化完后，再给最后一次机会
            try:
                product_link_locator.wait_for(state="visible", timeout=8000)
            except Exception:
                logger.error("   ❌ 彻底没搜到商品结果")
                return None, None

        logger.info(f"   成功找到商品卡片: {product_link_locator.inner_text()[:15]}...")

        # 5. 点击进入详情页
        with page.expect_popup(timeout=15000) as popup_info:
            product_link_locator.click()

        detail = popup_info.value
        detail.wait_for_load_state("domcontentloaded")

        # 6. 进入详情页后，也要净化
        clean_page_interference(detail)

        # ================= 提取数据 =================
        # 昨日销量
        yesterday_sales = ""
        try:
            raw = detail.locator("tr").filter(
                has_text=re.compile(r"\d{4}/\d{2}/\d{2}")
            ).first.locator("td").nth(1).inner_text().strip()
            yesterday_sales = raw.split("\n")[0].strip()
        except Exception as e:
            logger.warning(f"   ⚠️ 昨日销量抓取失败: {repr(e)}")

        # 近30日销量
        thirty_day_sales = ""
        try:
            thirty_day_sales = detail.locator(
                ".analysis-item:has(.analysis-label:text-is('近30日销量'))"
            ).locator(".analytics-value span.fs20, .analysis-value span.fs20").first.inner_text().strip()
        except Exception as e:
            logger.warning(f"   ⚠️ 近30日销量抓取失败: {repr(e)}")

        # ================= 模拟人类阅读行为 =================
        logger.info("   🐢 模拟人类停留...")
        detail.wait_for_timeout(random.randint(3000, 8000))

        try:
            detail.mouse.wheel(0, random.randint(200, 600))
            detail.wait_for_timeout(random.randint(800, 1500))
            detail.mouse.wheel(0, random.randint(-200, -100))
            detail.wait_for_timeout(random.randint(500, 1000))
            detail.mouse.move(
                random.randint(100, 800),
                random.randint(100, 600),
                steps=random.randint(5, 15)
            )
        except Exception:
            pass

        return yesterday_sales, thirty_day_sales

    except Exception as e:
        logger.error(f"   ❌ 搜索抓取异常: {repr(e)}")
        return None, None

    finally:
        if detail:
            detail.close()
