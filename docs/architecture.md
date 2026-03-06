# AI Shovel Index — Architecture

## 技术栈

| 层 | 选型 | 说明 |
|----|------|------|
| 语言 | Python 3.11+ | 全项目统一 |
| 爬虫 | Playwright (async) | 无头 Chromium，模拟真实浏览器访问闲鱼 |
| 存储 | SQLite (`data/index.db`) | 单文件，无需服务器，Git 可追踪 |
| 分析 | 纯 Python stdlib | 无外部依赖，纯计算 |
| 渲染 | HTML + Playwright screenshot + Jinja2 | 截图 4 张 1080×1080 PNG；CJK 字体由系统字体栈自动处理 |
| 自动化 | GitHub Actions | cron `0 2 * * *`，UTC+0 每日 02:00 触发 |
| 测试 | pytest | 单元测试覆盖 analyzer、renderer |
| 格式化 | black (line=100) + ruff | 非协商，CI 强制 |

---

## 目录结构

```
AI-Shovel-Index/
├── config.py              # 关键词列表、权重参数、路径常量、TypedDict 定义
├── crawler.py             # Playwright 爬闲鱼 → 写入 SQLite
├── analyzer.py            # 读 DB → 计算指数 → 返回 AnalysisResult
├── renderer.py            # AnalysisResult → PNG + post.txt
├── run_daily.py           # 串联全流程的入口（CLI）
│
├── data/
│   └── index.db           # SQLite 数据库（git 忽略，但结构在此记录）
│
├── output/                # 每日生成物（git 忽略）
│   ├── card1_index_YYYY_MM_DD.png
│   ├── card2_drivers_YYYY_MM_DD.png
│   ├── card3_cooling_YYYY_MM_DD.png
│   ├── card4_weekly_YYYY_MM_DD.png
│   └── post.txt
│
├── tests/
│   ├── fixtures/
│   │   ├── output/        # 渲染测试输出（可视化验证）
│   │   └── preview/       # preview_all.py 生成的预览图（git 忽略）
│   ├── test_analyzer.py
│   └── test_renderer.py
│
├── templates/
│   ├── card_index.html    # Card 1：核心指数仪表盘 + week_delta
│   ├── card_drivers.html  # Card 2：Top 4 驱动关键词排行榜
│   ├── card_cooling.html  # Card 3：退热信号列表（红色强调）
│   ├── card_weekly.html   # Card 4：Weekly Brief 叙述摘要
│   └── card.html          # 已废弃（保留备用，renderer 不再引用）
│
├── .github/
│   └── workflows/
│       └── daily.yml      # GitHub Actions 定时任务
│
├── requirements.txt
├── .gitignore
└── AGENTS.md
```

---

## 数据流

```
闲鱼搜索页
    ↓ Playwright (crawler.py)
SQLite: crawl_records 表
    ↓ 读取近8天数据 (analyzer.py)
AnalysisResult dict
    ↓ (renderer.py)
output/card1_index_YYYY_MM_DD.png
output/card2_drivers_YYYY_MM_DD.png
output/card3_cooling_YYYY_MM_DD.png
output/card4_weekly_YYYY_MM_DD.png
output/post.txt
```

---

## DB Schema

```sql
CREATE TABLE crawl_records (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    date         TEXT NOT NULL,        -- "YYYY-MM-DD"
    keyword      TEXT NOT NULL,
    item_count   INTEGER NOT NULL,
    seller_count INTEGER NOT NULL,
    avg_price    REAL NOT NULL,
    created_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(date, keyword)              -- 防止重复写入
);
```

---

## 模块接口契约

所有模块间通过 `TypedDict` 约束的 `dict` 传递数据，不共享任何全局状态。

### CrawlRecord（crawler.py → DB）
```python
class CrawlRecord(TypedDict):
    date: str          # "YYYY-MM-DD"
    keyword: str
    item_count: int    # 0 if crawl failed
    seller_count: int
    avg_price: float
```

### AnalysisResult（analyzer.py → renderer.py）
```python
class AnalysisResult(TypedDict):
    date: str                  # "YYYY-MM-DD"
    index: float               # 0.0–100.0
    status: str                # "cold"|"early"|"rising"|"speculation"|"bubble"
    rankings: list[dict]       # [{"keyword": str, "growth": float}, ...]
    warming_up: bool           # True if DB has fewer than 7 days of data
    week_delta: float          # today's index minus oldest-day index in 7-day window; 0.0 if warming_up
```

---

## 指数计算逻辑

```python
# 最近7天（不含今日）均值
avg_items_7d   = mean(item_count for past 7 days per keyword)
avg_sellers_7d = mean(seller_count for past 7 days per keyword)

# 增长率（每关键词）
growth_items   = today_items / avg_items_7d      # 默认 1.0 if no history
growth_sellers = today_sellers / avg_sellers_7d

# 单关键词得分
kw_score = (growth_items * 0.6 + growth_sellers * 0.4) * 50

# 综合指数 = 所有关键词得分的加权均值，最终 clamp 到 [0, 100]
index = min(mean(kw_scores), 100.0)
```

### 状态区间
```
0–20   → cold
20–40  → early
40–60  → rising
60–80  → speculation
80–100 → bubble
```

### 冷启动
- DB 数据天数 < 7：用现有天数均值替代 7 天均值，`warming_up = True`
- DB 数据天数 = 1（仅今日）：`growth = 1.0`（基准），`warming_up = True`

---

## 渲染规格

**尺寸**：1080 × 1080 px（标准社交媒体 1:1 正方形）

**输出卡片**（4张 PNG + 1个 post.txt）：

| 卡片 | 模板 | 内容 |
|------|------|------|
| Card 1 | `card_index.html` | 核心指数仪表盘（半圆形）、超大数字、week_delta (↑/↓)、`@yoyoostone` |
| Card 2 | `card_drivers.html` | Top 4 驱动关键词排行榜 + 进度条 |
| Card 3 | `card_cooling.html` | 退热信号列表（红色强调），无数据时显示 empty state |
| Card 4 | `card_weekly.html` | Weekly Brief 叙述摘要（Rising Fast + Cooling Down 分节） |

**视觉风格**：苹果发布会 PPT 风格
- 背景：深色（`#0a0a0a`）
- 主色：纯白（`#ffffff`）
- 强调色：按状态变化
  - cold → `#4a9eff`（冷蓝）
  - early → `#a8e6cf`（浅绿）
  - rising → `#ffd93d`（琥珀黄）
  - speculation → `#ff6b35`（橙红）
  - bubble → `#ff2d55`（苹果红）
- 字体：系统字体回退链（SF Pro → Helvetica Neue → Arial）
- 页脚品牌：`@yoyoostone`

**输出文件**：
- `output/card1_index_YYYY_MM_DD.png`
- `output/card2_drivers_YYYY_MM_DD.png`
- `output/card3_cooling_YYYY_MM_DD.png`
- `output/card4_weekly_YYYY_MM_DD.png`
- `output/post.txt`（纯文本，可直接粘贴发布）

---

## GitHub Actions 配置要点

```yaml
# .github/workflows/daily.yml 关键节点
on:
  schedule:
    - cron: '0 2 * * *'   # UTC 02:00，对应北京时间 10:00
  workflow_dispatch:       # 支持手动触发

# 必须安装的系统依赖（Playwright Chromium 需要）
- name: Install system deps
  run: sudo apt-get install -y libgbm-dev libasound2 ...

# 输出物作为 artifact 上传（可下载验证）
- uses: actions/upload-artifact@v4
  with:
    name: daily-output
    path: output/
```

---

## 已知风险与缓解

| 风险 | 描述 | 缓解策略 |
|------|------|---------|
| 闲鱼反爬 | 页面结构变更或 IP 封禁 | 随机 UA、请求延迟、错误时写 0 记录不中断流程 |
| GitHub Actions IP 被封 | 固定 IP 段易被识别 | 暂不处理，后续可引入代理或改用本地 cron |
| 冷启动数据不足 | 前7天无法计算增长率 | `warming_up` 降级逻辑，取现有天数均值 |
| Pillow 字体缺失 | CI 环境无中文字体 | 内嵌 fallback 英文字体；关键词显示用 Unicode 转义兜底 |
