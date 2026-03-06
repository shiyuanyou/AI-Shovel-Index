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
  - [x] Playwright Chromium headless 截图（1200×630 固定 viewport + clip）
  - [x] `warming_up=True` 时在图片和 post.txt 显示 "(warming up)"
  - [x] `post.txt` 格式：日期、得分、状态、关键词排行、hashtag
  - [x] `requirements.txt` 新增 `jinja2>=3.1.0`
  - [x] `config.py` 新增 `TEMPLATES_DIR` 路径常量
- [x] 创建 `tests/test_renderer.py`（接口不变，40/40 全通过）

**验收标准**：`python3 -m pytest tests/ -v` 40/40 全部通过。✅ 2026-03-06

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

- [ ] `pytest tests/ -v` 全部通过
- [ ] `black . --line-length 100 --check` 无报错
- [ ] `ruff check .` 无报错
- [ ] `mypy . --ignore-missing-imports` 无 error 级别报错
- [ ] GitHub Actions 手动触发一次，artifact 可下载验证

---

## 设计决策记录

| 日期 | 决策 | 原因 |
|------|------|------|
| 2026-03-06 | 爬虫用 Playwright 而非 requests | 闲鱼无公开 API，需浏览器渲染 |
| 2026-03-06 | 图片渲染改为 HTML + Playwright + Jinja2 | Playwright 已是依赖，CJK 字体由系统字体栈自动处理，布局更易维护 |
| 2026-03-06 | 风格参考苹果发布会 PPT | 深色+精准数据展示，高辨识度 |
| 2026-03-06 | 存储用 SQLite | 单文件，无服务器依赖，结构化查询简单 |
| 2026-03-06 | data/index.db 纳入 git 追踪 | GitHub Actions 需跨 run 累积历史数据；journal/wal 仍忽略 |
