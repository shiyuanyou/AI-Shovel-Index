# AI Shovel Index — MVP Context

## 1. 目标

构建一个**极简数据指数系统**，通过抓取二手平台上与 AI 相关的“教程/副业/部署”等商品数据，生成一个每日更新的 **AI 投机热度指数**。

用途：

* 用于社交媒体传播
* 每日生成一张可截图的指数图
* 形成连续更新的市场情绪观察

该项目 **不考虑商业化**，只关注：

* 话题度
* 可传播性
* 持续更新

核心问题：

普通人很难判断一个新技术概念是否已经进入 **投机阶段（卖铲子阶段）**。

该指数通过观察 **教程和副业类商品数量变化** 来反映市场情绪。

---

# 2. 数据来源

平台：

* Xianyu（闲鱼）

关键词示例：

```
ChatGPT 部署
Sora 教程
AI 副业
Stable Diffusion 教程
```

每天抓取每个关键词的搜索结果。

---

# 3. 抓取字段

每个商品提取：

```
keyword
price
seller_id
publish_time
```

计算三个核心指标：

```
item_count
seller_count
avg_price
```

存储结构：

```
date
keyword
item_count
seller_count
avg_price
```

存储方式：

* SQLite 或 CSV

---

# 4. 指数计算逻辑

计算最近 7 天平均值：

```
avg_items_7d
avg_sellers_7d
```

增长率：

```
growth_items = today_items / avg_items_7d
growth_sellers = today_sellers / avg_sellers_7d
```

指数计算：

```
index = (growth_items * 0.6 + growth_sellers * 0.4) * 50
```

限制范围：

```
index = min(index, 100)
```

---

# 5. 指数区间定义

```
0–20   cold
20–40  early
40–60  rising
60–80  speculation
80–100 bubble
```

最终输出：

```
AI SHOVEL INDEX
Score: XX / 100
Status: speculation
```

---

# 6. 图片输出（社交媒体传播）

每日生成一张图片：

尺寸：

```
1200 × 630
```

图片内容：

```
Title:
AI Shovel Index

Score:
67 / 100

Status:
Speculation

Chart:
7-day item_count trend

Ranking:
Top keywords by growth
```

图片格式：

```
index_YYYY_MM_DD.png
```

---

# 7. 每日文本输出

同时生成一段文本：

```
AI Shovel Index #23

Sora 教程
+52%

AI 副业
+31%

ChatGPT 部署
-10%

Current Index
67 / 100

Status
SPECULATION
```

输出文件：

```
post.txt
```

用于社交媒体发布。

---

# 8. 系统架构

极简结构：

```
crawler.py
analyze.py
render.py
run_daily.py
```

数据流：

```
Xianyu
  ↓
crawler
  ↓
database
  ↓
analyze
  ↓
index score
  ↓
render
  ↓
png image
```

---

# 9. crawler 示例

```python
import requests

def fetch(keyword):
    url = f"https://api.search.xianyu.com/search?q={keyword}"
    r = requests.get(url)
    data = r.json()

    items = data["items"]

    prices = []
    sellers = set()

    for i in items:
        prices.append(i["price"])
        sellers.add(i["seller_id"])

    return {
        "item_count": len(items),
        "seller_count": len(sellers),
        "avg_price": sum(prices) / len(prices)
    }
```

---

# 10. render 示例

使用 matplotlib：

```python
import matplotlib.pyplot as plt

def render(index, history):

    plt.figure(figsize=(12,6))

    plt.plot(history)

    plt.title(f"AI Shovel Index: {index}")

    plt.savefig("index.png")
```

---

# 11. 自动化运行

使用 GitHub Actions 定时运行：

```
cron: 0 2 * * *
```

每日执行：

```
python run_daily.py
```

执行流程：

```
crawl
→ store
→ analyze
→ render
→ output
```

生成文件：

```
/output
  index.png
  post.txt
```

---

# 12. 代码规模

预计代码量：

```
crawler.py   ~60 lines
analyze.py   ~40 lines
render.py    ~60 lines
run_daily.py ~20 lines
```

总规模：

```
~180–200 lines
```

---

# 13. 项目核心定位

本项目本质是一个 **市场情绪信号源**：

```
技术发布
↓
教程/副业出现
↓
卖铲子市场扩大
↓
指数上升
↓
投机阶段
```

通过 **教程商品数量变化** 来观测技术投机周期。

