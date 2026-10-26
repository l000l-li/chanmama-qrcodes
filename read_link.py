# read_link.py
import json
import logging

import requests

import config
from utils import setup_logging

logger = logging.getLogger(__name__)


def call_airscript(**kwargs):
    """调 AirScript 读 WPS 链接列，返回一维数组；失败返回 None。"""
    payload = {"Context": {"argv": kwargs}}
    headers = {
        "Content-Type": "application/json",
        "AirScript-Token": config.AIRSCRIPT_TOKEN,
    }
    try:
        r = requests.post(config.AIRSCRIPT_WEBHOOK_LINKS, json=payload, headers=headers, timeout=60)
        resp = r.json()
    except Exception as e:
        logger.error(f"读取链接请求异常: {repr(e)}")
        return None

    # 有错误，打印出来
    if resp.get("error"):
        logger.error(f"❌ AirScript 报错: {resp['error']}")
        logger.error(f"详情: {resp.get('error_details')}")
        return None

    # 拿返回值（云端脚本没有顶层 return 时，平台固定返回字符串 "[Undefined]"）
    result = resp.get("data", {}).get("result")
    if not result or result == "[Undefined]":
        logger.warning("⚠️ 云端脚本没有返回值：检查脚本最后有没有 return，且已 Ctrl+S 保存")
        logger.warning(f"完整返回: {resp}")
        return None

    # 正常是 JSON 字符串，个别环境会直接返回数组/对象
    if isinstance(result, str):
        try:
            data = json.loads(result)
        except Exception as e:
            logger.warning(f"⚠️ 解析结果失败: {e}")
            logger.warning(f"原始 result: {result}")
            return None
    else:
        data = result

    # 读整列时云端可能返回二维数组 [["链接"], ["链接"]]，拍平成一维
    if isinstance(data, list) and data and isinstance(data[0], list):
        data = [row[0] if isinstance(row, list) and row else row for row in data]

    return data


if __name__ == "__main__":
    setup_logging()
    links = call_airscript()
    if links:
        logger.info(f"✅ 共 {len(links)} 个商品")
        for item in links:
            logger.info(item)
    else:
        logger.error("❌ 没拿到数据")
