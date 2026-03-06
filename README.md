# VC Radar

聚合 Paul Graham、Hacker News、Sam Altman、Fred Wilson、Benedict Evans 五个数据源的博客与资讯，提供 Web 仪表盘和 CLI 两种使用方式。

<!-- 截图占位：将实际截图放到 docs/screenshot.png 后取消注释 -->
<!-- ![Dashboard Screenshot](docs/screenshot.png) -->

## 🚀 快速启动（新方式 - 支持实时刷新）

### 第一步：启动API服务器（必需）

打开**新终端窗口**，运行：

```bash
cd "News about VC"
python3 scripts/api_server.py
```

你会看到：
```
🚀 VC雷达 API服务器已启动
   地址: http://localhost:8081
   刷新接口: http://localhost:8081/api/refresh
```

**保持此窗口运行！**

### 第二步：启动Web服务器

在**另一个终端窗口**，运行：

```bash
cd "News about VC"
python3 -m http.server 8080 --directory static
```

### 第三步：打开浏览器

访问：http://localhost:8080

点击 **"📡 实时刷新"** 按钮即可重新爬取最新数据！

## 📡 实时刷新功能

点击页面右上角的 **"📡 实时刷新"** 按钮，系统会：

1. 🔄 重新爬取5个VC源的最新内容
2. 📊 获取比之前更多的数据（每站最多50条）
3. 💾 更新数据库
4. 📱 页面自动显示最新内容（按时间排序）

## 📊 当前数据量

- **数据库总量**: 163条（可继续增长）
- **显示方式**: 按发布时间排序，最新内容在前
- **数据来源**:
  - Paul Graham: 48条
  - Sam Altman: 46条  
  - Hacker News: 29条
  - Fred Wilson: 20条
  - Benedict Evans: 20条

## 数据源

| 来源 | 网址 | 抓取方式 |
|------|------|----------|
| Paul Graham | paulgraham.com | HTML 解析 |
| Hacker News | news.ycombinator.com | HTML 解析 |
| Sam Altman | blog.samaltman.com | HTML 解析 |
| Fred Wilson / AVC | avc.xyz | RSS Feed |
| Benedict Evans | ben-evans.com | RSS Feed |

## CLI 用法

### 手动刷新数据

```bash
# 刷新全部数据源（最大化获取）
python3 scripts/refresh_data.py
```

### 多站点抓取

```bash
# 抓取全部站点
python main.py multi-crawl --all

# 只抓取指定站点
python main.py multi-crawl --pg --hn        # Paul Graham + Hacker News
python main.py multi-crawl --sa --fw --be   # Sam Altman + Fred Wilson + Benedict Evans

# 限制每站点最大条目数
python main.py multi-crawl --all --max-items 50
```

站点缩写：`--pg` Paul Graham / `--hn` Hacker News / `--sa` Sam Altman / `--fw` Fred Wilson / `--be` Benedict Evans

### 查看与筛选

```bash
python main.py list                         # 列出已抓取的标题
python main.py list --source hackernews     # 按来源过滤
python main.py list --limit 20              # 限制显示条数
python main.py list --refresh               # 先刷新再列出
```

## 项目结构

```
news_about_vc/
├── main.py                  # CLI 入口
├── scripts/
│   ├── api_server.py        # API服务器（实时刷新后端）
│   └── refresh_data.py      # 数据刷新脚本
├── static/
│   ├── index.html           # Web仪表盘
│   └── data.json            # 数据文件
├── vc_tracker/
│   ├── multi_crawler.py     # 多站点爬虫
│   ├── crawler.py           # 单站点爬虫
│   ├── analyzer.py          # 数据分析
│   └── visualizer.py        # 图表可视化
├── data/                    # 运行时数据
└── output/                  # 输出目录
```

## 🛠️ 故障排除

### 点击刷新后提示"请先启动API服务器"

**原因**: API服务器没有运行

**解决**: 新建终端运行 `python3 scripts/api_server.py`

### 页面加载失败

**原因**: Web服务器没有运行

**解决**: 运行 `python3 -m http.server 8080 --directory static`

### 如何停止服务

按 `Ctrl+C` 在对应的终端窗口中停止服务

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3 |
| Web服务 | http.server (标准库) |
| API服务 | http.server (自定义Handler) |
| 爬虫 | requests, BeautifulSoup4, feedparser, lxml |
| 数据分析 | pandas |
| 前端 | 原生 HTML5 + CSS3 + JavaScript |

## License

MIT
