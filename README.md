# VC Radar

聚合 Paul Graham、Hacker News、Sam Altman、Fred Wilson、Benedict Evans 五个数据源的博客与资讯，提供 Web 仪表盘和 CLI 两种使用方式。

<!-- 截图占位：将实际截图放到 docs/screenshot.png 后取消注释 -->
<!-- ![Dashboard Screenshot](docs/screenshot.png) -->

## 数据源

| 来源 | 网址 | 抓取方式 |
|------|------|----------|
| Paul Graham | paulgraham.com | HTML 解析 |
| Hacker News | news.ycombinator.com | HTML 解析 |
| Sam Altman | blog.samaltman.com | Atom Feed |
| Fred Wilson / AVC | avc.xyz | RSS Feed |
| Benedict Evans | ben-evans.com | RSS Feed |

## 快速开始

```bash
# 安装依赖
make install

# 抓取全部数据源
make crawl

# 启动 Web 仪表盘 (localhost:8081)
make serve
```

浏览器访问 `http://localhost:8081`，点击「刷新」按钮即可实时抓取最新数据。

静态版本部署在 GitHub Pages，通过 `static/index.html` 加载 `static/data.json` 展示数据。

## Makefile 命令

| 命令 | 说明 |
|------|------|
| `make install` | 安装 Python 依赖 |
| `make crawl` | 抓取全部 5 个数据源 |
| `make serve` | 启动 Web 服务器 (端口 8081) |
| `make stop` | 停止 Web 服务器 |
| `make restart` | 重启 Web 服务器 |
| `make test` | 运行 pytest 测试套件 |
| `make clean` | 清理 `__pycache__` 和临时文件 |

## CLI 用法

所有命令通过 `python main.py <子命令>` 调用。

### 多站点抓取

```bash
# 抓取全部站点
python main.py multi-crawl --all

# 只抓取指定站点
python main.py multi-crawl --pg --hn        # Paul Graham + Hacker News
python main.py multi-crawl --sa --fw --be   # Sam Altman + Fred Wilson + Benedict Evans

# 限制每站点最大条目数
python main.py multi-crawl --all --max-items 20
```

站点缩写：`--pg` Paul Graham / `--hn` Hacker News / `--sa` Sam Altman / `--fw` Fred Wilson / `--be` Benedict Evans

### 查看与筛选

```bash
python main.py list                         # 列出已抓取的标题
python main.py list --source hackernews     # 按来源过滤
python main.py list --limit 20              # 限制显示条数
python main.py list --refresh               # 先刷新再列出
```

### 刷新数据

```bash
python main.py refresh --all                # 刷新全部数据源
python main.py refresh --pg --hn            # 刷新指定站点
```

### 分析与可视化

```bash
python main.py analyze                      # 赛道热度、轮次分布、时间趋势
python main.py visualize                    # 生成图表 (PNG + HTML)
python main.py report --format html         # 生成 HTML 分析报告
```

## 项目结构

```
news_about_vc/
├── main.py                  # CLI 入口
├── web_server.py            # Web 服务器 (端口 8081，内嵌前端)
├── gui_table.py             # 桌面 GUI 表格
├── Makefile                 # 常用命令快捷方式
├── requirements.txt         # Python 依赖
├── pytest.ini               # pytest 配置
├── config/
│   └── settings.py          # 全局配置 (目录、关键词、图表参数)
├── vc_tracker/
│   ├── __init__.py          # 包定义与版本号
│   ├── crawler.py           # 单站点爬虫
│   ├── multi_crawler.py     # 多站点爬虫 (5 源聚合、去重、原子写入)
│   ├── analyzer.py          # 数据分析 (pandas)
│   ├── visualizer.py        # 图表可视化
│   └── utils.py             # 工具函数 (HTML 报告生成等)
├── static/
│   ├── index.html           # GitHub Pages 静态页面
│   └── data.json            # 静态数据文件
├── tests/
│   ├── test_news_item.py    # NewsItem 单元测试
│   ├── test_multi_crawler.py # 多站点爬虫测试
│   └── test_integration_crawlers.py # 网络集成测试
├── data/                    # 运行时数据 (已 gitignore)
└── output/
    ├── charts/              # 生成的图表
    └── reports/             # 生成的报告
```

## 技术栈

| 类别 | 技术 |
|------|------|
| 语言 | Python 3 |
| Web 服务 | `http.server` (标准库) |
| 爬虫 | requests, BeautifulSoup4, feedparser, lxml |
| 数据分析 | pandas |
| 可视化 | matplotlib, seaborn, plotly, wordcloud, jieba |
| 测试 | pytest |
| 部署 | GitHub Actions + GitHub Pages |

## 主要特性

- **标题去重** -- 基于标题自动去重，避免重复条目
- **随机排序** -- 每次加载随机打乱显示顺序
- **XSS 防护** -- 前端 `escapeHtml` / `sanitizeUrl` 防注入
- **线程安全** -- 爬虫使用 `threading.Lock` 保护并发访问
- **原子写入** -- 数据保存使用 `os.replace` 确保文件完整性
- **响应式布局** -- Web 仪表盘适配桌面和移动端

## License

MIT
