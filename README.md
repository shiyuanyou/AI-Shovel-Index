# AI Shovel Index

AI Shovel Index 是一个每日更新的 AI 市场情绪快照项目。

它会抓取闲鱼上的 AI 教程/副业相关商品数据，计算一个 `0-100` 的热度指数，并输出适合社交媒体发布的 3 张卡片和一份 `post.txt`。

## 项目做什么

- 抓取闲鱼 AI 相关关键词的商品数量与卖家数量
- 计算每日指数与阶段状态
- 渲染 3 张 `1080x1080` PNG 卡片
- 生成可直接发布的文案 `post.txt`

当前主流程：

```text
crawler.py -> SQLite -> analyzer.py -> renderer.py -> 3 PNGs + post.txt
```

## 当前输出

- `card1_index_YYYY_MM_DD.png`
- `card2_daily_YYYY_MM_DD.png`
- `card3_weekly_YYYY_MM_DD.png`
- `post.txt`

## 快速开始

本地运行：

```bash
/opt/homebrew/Caskroom/miniconda/base/envs/py312/bin/python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium
.venv/bin/python3 smoke_test.py
.venv/bin/python3 run_daily.py
```

如果只是先验证渲染环境是否正常，优先运行：

```bash
.venv/bin/python3 smoke_test.py
```

## 部署方式

当前仓库支持两条推荐路径：

- 原生 VPS + `systemd timer`
- Docker Compose + `systemd timer`

如果你更关心升级和回滚，优先看 Docker 路径。

## 文档入口

- 产品目标：`docs/vision.md`
- 当前架构：`docs/architecture.md`
- 部署说明：`docs/deployment.md`
- Docker 部署：`deploy/docker/README.md`
- VPS 部署：`deploy/vps/README.md`
- 当前重构任务：`docs/stm_current.md`

## 项目特点

- 不做 Web 服务，只做每日批处理
- 使用 SQLite 保存历史数据
- 使用 Playwright + Chromium 做抓取和截图
- 日志中会输出 `CRAWL_SUMMARY`、`CRAWL_HEALTH`、`ANALYSIS_SUMMARY`、`OUTPUT_SUMMARY` 便于云端排障

## 适合谁

- 想观察 AI 话题情绪变化的人
- 想把“卖铲子阶段”做成日更内容的人
- 想部署一个轻量批处理数据产品的人
