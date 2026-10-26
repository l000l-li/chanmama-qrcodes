# utils.py
import base64
import logging
import os
import random
import time

import requests

import config

logger = logging.getLogger(__name__)


def setup_logging():
    """日志同时输出到控制台和 logs/chanmama.log，重复调用不会重复挂 handler。"""
    root = logging.getLogger()
    if root.handlers:
        return
    root.setLevel(logging.INFO)

    os.makedirs(config.LOG_DIR, exist_ok=True)
    file_handler = logging.FileHandler(
        os.path.join(config.LOG_DIR, "chanmama.log"), encoding="utf-8"
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    )
    root.addHandler(file_handler)

    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(message)s"))
    root.addHandler(console)


def human_delay(min_sec=2.0, max_sec=5.0):
    """随机延迟，模拟真人停顿"""
    time.sleep(random.uniform(min_sec, max_sec))


def simulate_human(page):
    """模拟真人：随机滚动 + 随机鼠标移动"""
    try:
        for _ in range(random.randint(1, 3)):
            page.mouse.wheel(0, random.randint(100, 500))
            time.sleep(random.uniform(0.3, 1.0))
        page.mouse.move(
            random.randint(100, 1200),
            random.randint(100, 700),
            steps=random.randint(5, 15)
        )
        time.sleep(random.uniform(0.2, 0.8))
    except Exception:
        pass


def upload_qrcode_to_github(img_bytes, filename):
    """上传二维码到 GitHub，返回 jsDelivr CDN 链接"""
    if not img_bytes:
        return ""
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/contents/qrcodes/{filename}"
    content = base64.b64encode(img_bytes).decode()
    headers = {
        "Authorization": f"token {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }
    data = {
        "message": f"add {filename}",
        "content": content,
        "branch": config.GITHUB_BRANCH,
    }
    try:
        r = requests.put(url, json=data, headers=headers, timeout=30)
        if r.status_code in (200, 201):
            return f"https://cdn.jsdelivr.net/gh/{config.GITHUB_REPO}@{config.GITHUB_BRANCH}/qrcodes/{filename}"
        elif r.status_code == 422:
            logger.info("   文件已存在，跳过上传")
            return f"https://cdn.jsdelivr.net/gh/{config.GITHUB_REPO}@{config.GITHUB_BRANCH}/qrcodes/{filename}"
        else:
            logger.error(f"   上传失败: {r.status_code} {r.text[:200]}")
            return ""
    except Exception as e:
        logger.error(f"   上传异常: {repr(e)}")
        return ""


# ============ 滑块处理 ============

def has_slider(page):
    """判断当前页面有没有阿里云滑块（立刻返回，不等待）"""
    try:
        slider = page.locator("#aliyunCaptcha-sliding-slider")
        return slider.count() > 0 and slider.is_visible()
    except Exception:
        return False


def handle_slider_if_present(page, max_retry=3, wait_sec=2):
    """
    先等 wait_sec 秒看滑块会不会出现，出现就拖，没出现就跳过。
    这样能处理"滑块比检测晚出现"的情况。
    """
    logger.debug("   等待滑块出现...")
    try:
        page.wait_for_selector(
            "#aliyunCaptcha-sliding-slider",
            state="visible",
            timeout=wait_sec * 1000,
        )
        logger.debug("   滑块出现了！")
    except Exception:
        logger.debug("   没等到滑块，跳过")
        return False

    # 滑块出现了，开始拖
    for attempt in range(max_retry):
        logger.info(f"   ⚠️ 检测到滑块，第 {attempt + 1} 次尝试...")
        try:
            drag_aliyun_slider(page)
            human_delay(2, 4)
            if not has_slider(page):
                logger.info("   ✅ 滑块已通过")
                return True
            else:
                logger.warning("   ⚠️ 滑块还在，重试...")
                human_delay(2, 3)   # 给阿里云重置时间
        except Exception as e:
            logger.warning(f"   ⚠️ 第 {attempt + 1} 次失败: {repr(e)}")
            human_delay(2, 3)

    logger.error("   ❌ 滑块多次尝试未通过")
    return False

def close_popup_if_present(page):
    """
    检测并关闭蝉妈妈的双11等活动弹窗
    返回 True 表示关闭了，False 表示没有弹窗
    """
    try:
        # 1. 先找有没有弹窗的特征元素（那个带图片的容器）
        popup = page.locator(".relative:has(img.img-bg)").first

        # 如果弹窗存在且可见
        if popup.count() > 0 and popup.is_visible():
            # 2. 找弹窗里的关闭按钮（那个 X 的 svg）
            # 一般这种按钮的 class 会包含 close，或者直接包裹在 svg 里
            close_btn = popup.locator("svg[pid='0'], .close, [class*='close']").first

            if close_btn.count() > 0:
                close_btn.click(timeout=3000)
            else:
                # 如果找不到关闭按钮的 class，就点击弹窗遮罩的空白处，或者强制按 ESC
                page.keyboard.press("Escape")

            logger.info("   🧹 已关闭活动弹窗")
            human_delay(1, 2)
            return True
    except Exception:
        pass
    return False
def clean_page_interference(page, timeout_sec=15):
    """
    超级净化器：循环清理页面上的弹窗和滑块，直到页面干净为止。
    返回 True 表示清理完毕，False 表示超时仍未清理干净。
    """
    start_time = time.time()

    while time.time() - start_time < timeout_sec:
        # 1. 查弹窗
        has_popup = False
        try:
            popup = page.locator(".relative:has(img.img-bg)").first
            if popup.count() > 0 and popup.is_visible():
                close_btn = popup.locator("svg[pid='0'], .close, [class*='close']").first
                if close_btn.count() > 0:
                    close_btn.click(timeout=2000)
                else:
                    page.keyboard.press("Escape")
                logger.info("   🧹 已强制关闭活动弹窗")
                has_popup = True
                page.wait_for_timeout(500)
        except Exception:
            pass

        # 2. 查滑块 (复用你之前的 has_slider 和 drag_aliyun_slider)
        has_slider_flag = False
        try:
            if has_slider(page):
                logger.warning("   ⚠️ 发现滑块，正在尝试拖拽...")
                drag_aliyun_slider(page)
                has_slider_flag = True
                page.wait_for_timeout(2000) # 等验证结果
        except Exception:
            pass

        # 如果既没有弹窗，也没有滑块，说明页面干净了，跳出循环
        if not has_popup and not has_slider_flag:
            return True

        # 如果有拦截，稍微等一下再查（因为拖完滑块可能还会再弹）
        page.wait_for_timeout(500)

    logger.warning("   ❌ 警告：页面拦截清理超时！")
    return False
def drag_aliyun_slider(page):
    """
    拖动阿里云滑块到最右（优化版）。
    随机步长 + 上下抖动 + 终点回拉微调 + 随机停顿。
    """
    slider = page.locator("#aliyunCaptcha-sliding-slider")
    box = slider.bounding_box()
    if not box:
        raise Exception("滑块不可见")

    start_x = box["x"] + box["width"] / 2
    start_y = box["y"] + box["height"] / 2

    # 容器宽度算距离
    container = page.locator("#aliyunCaptcha-sliding-body")
    cbox = container.bounding_box()
    if not cbox:
        raise Exception("容器不可见")
    distance = cbox["width"] - box["width"]

    # 按下前，随机停一下
    page.mouse.move(start_x, start_y)
    time.sleep(random.uniform(0.2, 0.5))
    page.mouse.down()
    time.sleep(random.uniform(0.3, 0.6))

    # 分段拖动：步长随机 15~25，加轻微抖动
    moved = 0
    while moved < distance:
        step = random.randint(15, 25)
        moved = min(moved + step, distance)
        page.mouse.move(
            start_x + moved,
            start_y + random.randint(-1, 1),   # 上下轻微抖动
            steps=random.randint(2, 4),
        )
        time.sleep(random.uniform(0.03, 0.08))   # 每步随机停顿

    # 终点微调：先回拉 2~5 像素，再推回去
    time.sleep(random.uniform(0.1, 0.3))
    pull_back = random.randint(2, 5)
    page.mouse.move(start_x + distance - pull_back, start_y, steps=2)
    time.sleep(random.uniform(0.05, 0.15))
    page.mouse.move(start_x + distance, start_y, steps=2)

    # 松开前，停一下
    time.sleep(random.uniform(0.2, 0.5))
    page.mouse.up()
    time.sleep(2)
