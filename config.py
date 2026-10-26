# config.py
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")


def _load_env(path):
    """把 .env 的键值读进环境变量，已存在的环境变量优先（不覆盖）。"""
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _path_env(name, default_name):
    """读路径配置；相对路径一律相对项目目录解析。"""
    value = os.getenv(name)
    if not value:
        return os.path.join(BASE_DIR, default_name)
    if os.path.isabs(value):
        return value
    return os.path.join(BASE_DIR, value)


def _bool_env(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _int_env(name, default):
    try:
        return int(os.getenv(name, default))
    except ValueError:
        return default


_load_env(ENV_PATH)

# 路径
RAW_COOKIE_PATH = _path_env("CHANMAMA_COOKIE_PATH", "chanmama_raw.json")
EXCEL_PATH = _path_env("EXCEL_PATH", "禅妈妈商品链接记录表.xlsx")
LOG_DIR = _path_env("LOG_DIR", "logs")

# GitHub 图床
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_REPO = os.getenv("GITHUB_REPO", "")
GITHUB_BRANCH = os.getenv("GITHUB_BRANCH", "main")

# URL
START_URL = "https://www.chanmama.com/douyin/"
BASE_URL = "https://www.chanmama.com"

# AirScript
AIRSCRIPT_TOKEN = os.getenv("AIRSCRIPT_TOKEN", "")
AIRSCRIPT_WEBHOOK_A = os.getenv("AIRSCRIPT_WEBHOOK_A", "")
AIRSCRIPT_WEBHOOK_B = os.getenv("AIRSCRIPT_WEBHOOK_B", "")
AIRSCRIPT_WEBHOOK_LINKS = os.getenv("AIRSCRIPT_WEBHOOK_LINKS", "")

# 浏览器
HEADLESS = _bool_env("HEADLESS", False)
SLOW_MO = _int_env("SLOW_MO", 100)


def missing_settings():
    """返回缺失的必填配置项名称，便于启动时一次性告警。"""
    required = {
        "AIRSCRIPT_TOKEN": AIRSCRIPT_TOKEN,
        "AIRSCRIPT_WEBHOOK_A": AIRSCRIPT_WEBHOOK_A,
        "AIRSCRIPT_WEBHOOK_B": AIRSCRIPT_WEBHOOK_B,
        "AIRSCRIPT_WEBHOOK_LINKS": AIRSCRIPT_WEBHOOK_LINKS,
        "GITHUB_TOKEN": GITHUB_TOKEN,
        "GITHUB_REPO": GITHUB_REPO,
    }
    return [name for name, value in required.items() if not value]
