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

- [x] 创建 `renderer.py`
  - [x] `render(result: AnalysisResult, output_dir?) -> tuple[Path, Path]`：生成 PNG + post.txt
  - [x] 苹果发布会风格布局（深色背景、状态色、分栏排版、网格线）
  - [x] `warming_up=True` 时在图片和 post.txt 显示 "(warming up)"
  - [x] `post.txt` 格式：日期、得分、状态、关键词排行、hashtag
  - [x] 字体回退链（macOS + Linux CI 均兼容）
- [x] 创建 `tests/test_renderer.py`
  - [x] `test_render_output_files`：验证 PNG 和 post.txt 生成
  - [x] `test_render_image_size`：验证图片尺寸 1200×630
  - [x] `test_render_warming_up_label`：验证 warming_up 标签
  - [x] 5种状态全部渲染无报错
  - [x] 视觉预览图保存至 `tests/fixtures/output/`
  - [x] 共20个测试，全部通过

**验收标准**：`pytest tests/test_renderer.py -v` 全部通过。✅ 2026-03-06（20/20 passed）

---

## Phase 3：爬虫模块

- [ ] 创建 `crawler.py`
  - [ ] `fetch_keyword(keyword: str, page) -> CrawlRecord`：Playwright 爬单个关键词
  - [ ] `crawl_all(date: str) -> list[CrawlRecord]`：遍历所有关键词，失败写 0 记录
  - [ ] `save_records(records: list[CrawlRecord]) -> None`：批量写入 DB
  - [ ] `--dry-run` CLI flag：打印结果不写 DB
  - [ ] `--keyword` CLI flag：仅爬单个关键词
  - [ ] 闲鱼搜索页解析逻辑（商品数、卖家去重、均价）
  - [ ] 随机 UA + 请求延迟（反反爬基础措施）

**验收标准**：`python crawler.py --keyword "AI 副业" --dry-run` 在本地返回非零 item_count。

> **注意**：闲鱼页面结构需实际抓包确认，此 Phase 最复杂，预期需要调试迭代。

---

## Phase 4：集成与自动化

- [ ] 创建 `run_daily.py`
  - [ ] 串联 crawl → analyze → render
  - [ ] `--date` CLI flag（指定日期，用于补跑历史数据）
  - [ ] 全流程日志输出（INFO 级别）
  - [ ] 最终打印输出文件路径
- [ ] 创建 `.github/workflows/daily.yml`
  - [ ] `cron: '0 2 * * *'`（UTC，对应北京时间 10:00）
  - [ ] `workflow_dispatch` 支持手动触发
  - [ ] 安装 Python 3.11 + pip 依赖
  - [ ] 安装 Playwright Chromium 及系统依赖
  - [ ] 运行 `python run_daily.py`
  - [ ] 上传 `output/` 为 GitHub Actions artifact
  - [ ] 将 `data/index.db` commit 回仓库（保持历史数据）

**验收标准**：本地 `python run_daily.py` 端到端生成 PNG 和 post.txt；Actions workflow 手动触发成功。

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
| 2026-03-06 | 图片渲染用 Pillow 手绘 | matplotlib 视觉质感不适合社交传播 |
| 2026-03-06 | 风格参考苹果发布会 PPT | 深色+精准数据展示，高辨识度 |
| 2026-03-06 | 存储用 SQLite | 单文件，无服务器依赖，结构化查询简单 |
