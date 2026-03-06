# STM: v0 — MVP Build

**版本目标**：完整跑通 crawl → analyze → render → output 全流程，支持 GitHub Actions 每日自动运行。

**创建时间**：2026-03-06  
**当前状态**：BUILD 阶段

---

## Phase 1：基础设施 ✅

- [x] 创建 `config.py`（关键词列表、路径常量、TypedDict 定义、指数权重）
- [x] 创建 `requirements.txt`（playwright, pillow, pytest, black, ruff, mypy）
- [x] 创建 `.gitignore`（忽略 `data/`, `output/`, `__pycache__/`, `.venv/`）
- [x] 初始化 SQLite DB 结构（通过 `config.py` 中的 `init_db()` 函数）
- [x] 创建 `tests/` 目录结构（`__init__.py`, `fixtures/output/`）

**验收标准**：`python -c "from config import init_db; init_db()"` 无报错，`data/index.db` 创建成功。✅ 2026-03-06

---

## Phase 2a：分析模块 ✅

- [x] 创建 `analyzer.py`
  - [x] `get_records(date: str, days: int) -> list[CrawlRecord]`：从 DB 读取近 N 天数据
  - [x] `compute_index(records: list[CrawlRecord], today: str) -> AnalysisResult`：计算指数
  - [x] 冷启动逻辑：`days < 7` 时设置 `warming_up = True`
  - [x] `get_status(index: float) -> str`：区间映射
  - [x] `analyze(target_date: str) -> AnalysisResult`：便捷入口
- [x] 创建 `tests/test_analyzer.py`
  - [x] `test_cold_start_index`：仅1天数据时验证 `warming_up=True`
  - [x] `test_normal_index`：7天完整数据，验证指数范围 [0, 100]
  - [x] `test_status_mapping`：验证5个状态区间边界
  - [x] 共20个测试，全部通过

**验收标准**：`pytest tests/test_analyzer.py -v` 全部通过。✅ 2026-03-06（20/20 passed）

---

## Phase 2b：渲染模块 ✅

- [x] 创建 `renderer.py`（HTML + Playwright 截图方案，替代原 Pillow 手绘）
  - [x] `render(result: AnalysisResult, output_dir?) -> tuple[Path, Path]`：生成 PNG + post.txt
  - [x] 创建 `templates/card.html`：Jinja2 模板，深色 Apple Keynote 风格，左右分栏布局
  - [x] Playwright Chromium headless 截图（1200×1200 固定 viewport + clip）
  - [x] `warming_up=True` 时在图片和 post.txt 显示 "(warming up)"
  - [x] `post.txt` 格式：日期、得分、状态、关键词排行、hashtag
  - [x] `requirements.txt` 新增 `jinja2>=3.1.0`
  - [x] `config.py` 新增 `TEMPLATES_DIR` 路径常量
- [x] **视觉重设计（2026-03-06）**：1200×1200 正方形，新信息架构
  - [x] `config.py` `IMAGE_HEIGHT` 改为 1200
  - [x] `templates/card.html` 全面重写：Top Drivers / Cooling 两栏 + yoyoo.ai 页脚
  - [x] `renderer.py` `_build_context()` 更新：rankings 拆分为 drivers/cooling，新增 `_PHASE_LABELS`
  - [x] `tests/test_renderer.py` 更新：`(1200, 630)` → `(1200, 1200)`
  - [x] 5张 preview 图重新生成（`tests/fixtures/preview/`）
- [x] 创建 `tests/test_renderer.py`（40/40 全通过）

**验收标准**：`python3 -m pytest tests/ -v` 40/40 全部通过。✅ 2026-03-06（含视觉重设计）

---

## Phase 3：爬虫模块 ✅

- [x] 创建 `crawler.py`
  - [x] `_fetch_keyword_async(keyword, browser) -> CrawlRecord`：Playwright 爬单个关键词（2页）
  - [x] `crawl_all(target_date?, keywords?) -> list[CrawlRecord]`：遍历所有关键词，失败写 0 记录
  - [x] `save_records(records) -> None`：INSERT OR REPLACE 批量写入 DB
  - [x] `--dry-run` CLI flag：打印结果不写 DB
  - [x] `--keyword` CLI flag：仅爬单个关键词
  - [x] 随机 UA 轮换 + 请求延迟（基础反反爬）
  - [x] 按关键词独立 browser context（cookie 隔离）

**验收标准**：`python3 crawler.py --keyword "AI 副业" --dry-run` 在本地返回结果（item_count 取决于网络和反爬状态）。

---

## Phase 4：集成与自动化 ✅

- [x] 创建 `run_daily.py`
  - [x] 串联 crawl → analyze → render（4步骤日志）
  - [x] `--date` CLI flag（指定日期）
  - [x] 全流程 INFO 级别日志输出
  - [x] 最终 print 输出文件路径（供 CI 读取）
- [x] 创建 `.github/workflows/daily.yml`
  - [x] `cron: '0 2 * * *'`（UTC，对应北京时间 10:00）
  - [x] `workflow_dispatch` 支持手动触发（含 date 输入参数）
  - [x] 安装 Python 3.11 + pip 依赖
  - [x] 安装 Playwright Chromium 及系统依赖
  - [x] 运行 `python run_daily.py`
  - [x] 上传 `output/` 为 GitHub Actions artifact（保留30天）
  - [x] 将 `data/index.db` commit 回仓库（保持历史数据）
- [x] 修正 `.gitignore`：允许 `data/index.db` 被 git 追踪（只忽略 journal/wal 文件）

**验收标准**：本地 `python3 run_daily.py` 端到端生成 PNG 和 post.txt；Actions workflow 手动触发成功。

---

## 全局完成标准

- [x] `pytest tests/ -v` 全部通过（40/40）
- [x] `black . --line-length 100 --check` 无报错
- [x] `ruff check .` 无报错
- [x] `mypy . --ignore-missing-imports` 无 error 级别报报错
- [ ] GitHub Actions 手动触发一次，artifact 可下载验证

---

## Phase 5：4 卡片视觉重设计

**版本目标**：将单张大图拆成 4 张 1080×1080 社交媒体卡片，每张聚焦单一信息，提升可读性和传播性。

**创建时间**：2026-03-06
**当前状态**：BUILD 阶段

### 卡片定义

| 编号 | 文件 | 内容 |
|------|------|------|
| Card 1 | `card_index.html` | 核心指数 + 大仪表盘 + week_delta |
| Card 2 | `card_drivers.html` | Top 4 驱动因素排行榜 |
| Card 3 | `card_cooling.html` | 退热信号排行榜 |
| Card 4 | `card_weekly.html` | Weekly Brief 叙述摘要 |

### 任务列表

- [x] `config.py` — 新增 `AUTHOR_HANDLE = "@yoyoostone"` 常量
- [x] `analyzer.py` / `config.py` — `AnalysisResult` 新增 `week_delta: float` 字段（今日 index 与7天前 index 的差值）
- [x] `analyzer.py` — `compute_index()` 计算并填充 `week_delta`
- [x] `templates/card_index.html` — Card 1：大仪表盘，超大数字，week_delta，@yoyoostone
- [x] `templates/card_drivers.html` — Card 2：Top 4 驱动词，大字体进度条
- [x] `templates/card_cooling.html` — Card 3：退热词列表，红色强调
- [x] `templates/card_weekly.html` — Card 4：叙述摘要，新铲子 + 退热铲子自然语言描述
- [x] `renderer.py` — `render()` 截图 4 张，返回 `tuple[Path, Path, Path, Path, Path]`
- [x] `tests/test_analyzer.py` — 补充 `week_delta` 验证用例（4项）
- [x] `tests/test_renderer.py` — 更新断言（4 PNG + 1 txt，尺寸 1080×1080）
- [x] `preview_all.py` — 修复 `AnalysisResult` 构造（新增 `week_delta` 字段）
- [x] `run_daily.py` — 更新解包逻辑（5 返回值）
- [x] 废弃 `templates/card.html`（保留文件但不再被 renderer 引用）

**验收标准**：`pytest tests/ -v` 全部通过 ✅ 2026-03-06（50/50）；black/ruff/mypy 全部清洁。

---

## 设计决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-03-06 | 爬虫用 Playwright 而非 requests | 闲鱼无公开 API，需浏览器渲染 |
| 2026-03-06 | 图片渲染改为 HTML + Playwright + Jinja2 | Playwright 已是依赖，CJK 字体由系统字体栈自动处理，布局更易维护 |
| 2026-03-06 | 风格参考苹果发布会 PPT | 深色+精准数据展示，高辨识度 |
| 2026-03-06 | 存储用 SQLite | 单文件，无服务器依赖，结构化查询简单 |
| 2026-03-06 | data/index.db 纳入 git 追踪 | GitHub Actions 需跨 run 累积历史数据；journal/wal 仍忽略 |
| 2026-03-06 | 图片尺寸改为 1080×1080，拆为4张卡片 | 单卡信息聚焦，提升社交媒体传播性；1080×1080 是 Instagram/小红书 标准正方形尺寸 |
| 2026-03-06 | 页脚品牌改为 @yoyoostone | 与创作者社媒账号一致 |
