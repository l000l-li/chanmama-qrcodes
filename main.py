# main.py
import logging
import sys
import time

import config
from main_a import run_stage_a
from main_b import run_stage_b
from utils import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("🚀 开始执行每日自动化任务")
    start_time = time.time()

    missing = config.missing_settings()
    if missing:
        logger.error(f"缺少配置项: {', '.join(missing)}，请检查 .env")

    failed_stages = []

    try:
        run_stage_b()
    except Exception:
        logger.exception("❌ 阶段 B 发生严重错误中断！")
        failed_stages.append("B")

    logger.info("⏳ 阶段 B 结束，休息 10 秒后进入阶段 A...")
    time.sleep(10)

    try:
        run_stage_a()
    except Exception:
        logger.exception("❌ 阶段 A 发生严重错误中断！")
        failed_stages.append("A")

    logger.info(f"🎉 所有任务执行完毕！总耗时: {(time.time() - start_time) / 60:.1f} 分钟")
    if failed_stages:
        logger.error(f"本次失败的阶段: {', '.join(failed_stages)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
