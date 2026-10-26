# 禅妈妈商品数据自动化采集

基于 Playwright 的蝉妈妈（chanmama.com）抖音商品数据采集工具。用真实浏览器模拟人工操作绕过风控，把商品销量数据自动同步到金山文档（Kdocs）在线表格，并在本地 Excel 中维护已采集商品链接做查重。

## 功能

程序由两个阶段组成，串行执行：

### 阶段 B：更新已有商品销量

1. 通过 AirScript Webhook 读取 WPS 表格中的全部商品链接
2. 在 WPS 表格中新增「昨日」「前日」两列
3. 逐个链接到蝉妈妈搜索页搜索，打开详情页抓取「昨日销量」「近30日销量」
4. 单条失败重试 3 次，仍失败则写入「获取失败」占位
5. 按 `row = 2 * i` 对齐行号批量写回 WPS

### 阶段 A：发现新商品并追加

1. 读取本地 `禅妈妈商品链接记录表.xlsx`，构建已采集链接集合用于查重
2. 进入商品榜单列表页，逐页收集商品链接并打开详情页抓取字段
3. 过滤规则：
   - 品牌黑名单（`BRAND_BLACKLIST`，乔丹 / 安踏 / 李宁 等 20 个品牌）
   - 本地 Excel 中已存在的链接
   - 本页出现「昨日销量 < 500」的商品时，本页跑完即停止翻页
4. 新商品写入 WPS，**写入成功后**才把商品链接追加到本地 Excel（WPS 失败则不计入已采，下轮重试）

抓取的字段：店铺名称、商品图、商品链接、上架时间、二维码 URL、近30日销量、昨日销量。

## 目录结构

```
.
├── .env.example       # 配置模板，复制为 .env 后填值
├── .env               # 本地配置与密钥（已被 .gitignore 忽略）
├── .gitignore
├── main.py            # 入口：阶段 B → 休息 10s → 阶段 A
├── main_a.py          # 阶段 A 主流程
├── main_b.py          # 阶段 B 主流程
├── login.py           # 加载 cookie、创建已登录浏览器上下文（含反检测脚本）
├── crawl.py           # 列表页导航、链接收集、翻页
├── search_crawl.py    # 搜索页搜索、详情页弹窗抓销量（阶段 B）
├── parse.py           # 详情页字段解析、二维码抓取与上传
├── utils.py           # 日志初始化、拟人化延迟、滑块拖拽、弹窗清理、GitHub 图床
├── read_link.py       # AirScript 调用封装：读 WPS 全部链接
├── config.py          # 读取 .env，路径解析、图床、URL、浏览器开关
├── test.py            # 单链接调试脚本
├── logs/              # 运行日志（启动时自动创建）
├── chanmama_raw.json  # 蝉妈妈登录 cookie（已忽略提交）
└── 禅妈妈商品链接记录表.xlsx  # 本地查重表（仅存商品链接一列）
```

## 环境要求

- Windows（路径与桌面环境依赖）
- Python 3.9+
- 依赖：`playwright`、`requests`、`openpyxl`
- 可正常访问蝉妈妈、金山文档、GitHub 的网络环境

```powershell
pip install playwright requests openpyxl
playwright install chromium
```

直接用系统 Python 运行即可：

```powershell
python main.py
```

如需使用独立环境，先重建 `.venv`（旧环境可能已损坏）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install playwright requests openpyxl
.\.venv\Scripts\python.exe -m playwright install chromium
```

## 配置说明

配置分两层：

- **`.env`**：密钥与环境相关参数，本机私有，已被 `.gitignore` 忽略
- **[config.py](config.py)**：读取 `.env`（已存在的同名环境变量优先，不会被覆盖），并负责相对路径解析；`START_URL` / `BASE_URL` 等固定值直接写在文件里

首次运行前：

```powershell
Copy-Item .env.example .env
# 编辑 .env 填入真实值
```

| 变量 | 说明 |
|---|---|
| `CHANMAMA_COOKIE_PATH` | 蝉妈妈 cookie 文件，默认 `chanmama_raw.json` |
| `EXCEL_PATH` | 本地查重表路径，默认 `禅妈妈商品链接记录表.xlsx` |
| `LOG_DIR` | 日志目录，默认 `logs` |
| `GITHUB_TOKEN` / `GITHUB_REPO` / `GITHUB_BRANCH` | 二维码图床仓库，PAT 需 repo 写权限 |
| `AIRSCRIPT_TOKEN` | WPS AirScript 访问令牌 |
| `AIRSCRIPT_WEBHOOK_A` / `_B` / `_LINKS` | 阶段 A / 阶段 B / 读链接 三个云端脚本入口 |
| `HEADLESS` | `1` 时无窗口运行，默认 `0` |
| `SLOW_MO` | Playwright 每步操作间隔（毫秒），默认 `100` |

相对路径一律相对项目目录解析，因此可以从任意工作目录启动。启动时若必填项缺失，会在日志里一次性列出。

风控间隔（条间 3–6 秒、每 30 条长休 60–120 秒）目前在 `main_a.py` / `main_b.py` 中直接写死。

`chanmama_raw.json` 为 cookie 数组，需从已登录浏览器导出；登录态过期后需重新导出。

## 运行

```powershell
python main.py
```

- 日志同时输出到控制台和 `logs/chanmama.log`（含时间、级别、模块名）
- 退出码：`0` 表示两阶段均成功，`1` 表示至少一个阶段失败，便于定时任务判断
- 阶段 B 失败不会阻断阶段 A

单独运行某一阶段（各自会初始化日志）：

```powershell
python main_a.py
python main_b.py
```

调试单个链接的搜索抓取：

```powershell
python test.py
```

## WPS AirScript 接口约定

Python 端统一以如下格式 POST 到 Webhook：

```json
{
  "Context": {
    "argv": { "action": "<动作名>", "...": "其余参数" }
  }
}
```

请求头需带 `AirScript-Token`。已使用的动作：

| action | 用途 | 参数 |
|---|---|---|
| `append_new_products` | 阶段 A 追加新商品行 | `dataList`（数组，每项含 `shopName` / `imgUrl` / `link` / `listingDate` / `qrCodeUrl` / `thirtyDaySales` / `yesterdaySales`） |
| `prepare` | 阶段 B 新增日期列 | `yesterdayDate`、`beforeYesterdayDate` |
| `write_data` | 阶段 B 写回销量 | `dataList`（数组，每项含 `row` / `yesterdaySales` / `thirtyDaySales`） |

`read_link.py` 读取链接时，云端返回的二维数组会被拍平成字符串数组。

## 反风控策略

- 非 headless 启动 + `slow_mo`，禁用 `AutomationControlled`
- 注入脚本覆盖 `navigator.webdriver` / `languages` / `plugins`，伪造 `window.chrome`
- 随机鼠标移动、滚动、停留，条间随机 sleep，每 30 条强制长休息（60–120 秒）
- 阿里云滑块：分段拖动 + 上下抖动 + 终点回拉微调 + 随机停顿
- 页面净化器 `clean_page_interference`：循环清理活动弹窗与滑块，超时 15 秒

## 注意事项

1. **密钥已外置到 `.env`**：`.env` 与 `chanmama_raw.json` 均被 `.gitignore` 忽略。但旧 token 曾以明文存在于源码中，建议到 GitHub / 金山文档后台**吊销并重新生成**，再填入 `.env`。
2. **浏览器默认非 headless**：运行期间会弹出 Chromium 窗口，请勿手动操作或最小化，否则可能影响鼠标轨迹与点击定位。无人值守可设 `HEADLESS=1`，但更容易触发风控。
3. **写入失败会中断而不是静默继续**：阶段 A 中 WPS 写入失败则本条不计入已采、下轮重试；本地 Excel 写入失败会打印需要手工补录的链接（此时 WPS 已写入，下轮可能重复追加）。阶段 B 读取链接 / 新增列 / 写回 WPS 任一步失败都会抛错，`main.py` 记为阶段失败并返回非 0 退出码。
4. **依赖页面 DOM 选择器**：蝉妈妈前端改版会直接导致抓取失败，选择器集中在 `parse.py`、`crawl.py`、`search_crawl.py` 中便于维护。
