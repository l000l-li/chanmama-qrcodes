# parse.py
import base64
import logging
import re

from utils import simulate_human, upload_qrcode_to_github

logger = logging.getLogger(__name__)


def parse_qrcode(page, product_id, max_retry=3):
    """
    抓二维码，精确悬停"查看价格"，失败重试。
    返回 GitHub CDN URL，失败返回 ""
    """
    for attempt in range(max_retry):
        try:
            # 先把鼠标移开，避免干扰
            page.mouse.move(0, 0)
            page.wait_for_timeout(300)

            # 精确定位：最新到手价 格子里的 查看价格
            price_cell = page.locator(
                ".analysis-item:has(.analysis-label:text-is('最新到手价'))"
            ).first
            view_price = price_cell.locator("text=查看价格").first
            view_price.hover()

            # 等 tooltip 动画
            page.wait_for_timeout(800)

            # 只找可见的 tooltip 里的 canvas
            canvas = page.locator(".el-tooltip__popper:visible canvas").first
            canvas.wait_for(state="visible", timeout=5000)

            data_url = canvas.evaluate("el => el.toDataURL('image/png')")
            b64 = data_url.split(",")[1]
            img_bytes = base64.b64decode(b64)

            page.mouse.move(0, 0)

            filename = f"qrcode_{product_id}.png"
            url = upload_qrcode_to_github(img_bytes, filename)
            if url:
                return url

        except Exception as e:
            logger.warning(f"   二维码 第 {attempt + 1} 次失败: {repr(e)}")
            page.wait_for_timeout(1000)

    logger.warning("   二维码 多次尝试失败")
    return ""


def parse_detail(page, product_id):
    """抓所有字段 + 二维码"""
    data = {}

    # 1. 近30日销量
    try:
        data["近30日销量"] = page.locator(
            ".analysis-item:has(.analysis-label:text-is('近30日销量'))"
        ).locator(".analysis-value span.fs20").first.inner_text().strip()
    except Exception as e:
        data["近30日销量"] = ""
        logger.warning(f"   近30日销量 失败: {repr(e)}")

    # 2. 昨日销量（只取第一行，去掉后面的指数 1,791）
    try:
        raw = page.locator("tr").filter(
            has_text=re.compile(r"\d{4}/\d{2}/\d{2}")
        ).first.locator("td").nth(1).inner_text().strip()
        data["昨日销量"] = raw.split("\n")[0].strip()
    except Exception as e:
        data["昨日销量"] = ""
        logger.warning(f"   昨日销量 失败: {repr(e)}")

    # 3. 店铺名称（新增）
    try:
        data["店铺名称"] = page.locator(
            ".basic-item:has(.basic-label:text-is('小店'))"
        ).locator(".basic-value a").first.inner_text().strip()
    except Exception as e:
        data["店铺名称"] = ""
        logger.warning(f"   店铺名称 失败: {repr(e)}")

    # 4. 商品链接
    try:
        data["商品链接"] = page.locator(
            'a[href*="haohuo.jinritemai.com"]'
        ).first.get_attribute("href")
    except Exception:
        data["商品链接"] = ""

    # 5. 图片链接（截断到 .jpeg）
    try:
        page.wait_for_timeout(3000)
        img = page.locator('img[alt*="商品图"]').first
        raw = img.get_attribute("src") or img.get_attribute("data-src") or ""
        data["图片链接"] = raw.split("?")[0]
    except Exception:
        data["图片链接"] = ""

    # 6. 上架时间
    try:
        text = page.locator("div.mt6.fs12", has_text="首次上架").first.inner_text()
        m = re.search(r"首次上架：(\d{4}/\d{2}/\d{2})", text)
        data["上架时间"] = m.group(1) if m else ""
    except Exception:
        data["上架时间"] = ""

    # 7. 二维码
    data["二维码URL"] = parse_qrcode(page, product_id)

    return data


def handle_detail_page(page, product_id):
    """详情页：模拟真人 + 抓字段"""
    simulate_human(page)

    data = parse_detail(page, product_id)
    logger.info(f"   抓到: {data}")
    return data
