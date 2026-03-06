# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 主程序入口
支持多站点：Paul Graham, Hacker News, Sam Altman, Fred Wilson, Benedict Evans
"""

import os
import sys
import argparse
import logging
import json
from datetime import datetime
from typing import List, Dict

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import DATA_DIR, REPORTS_DIR, CHARTS_DIR
from vc_tracker.crawler import Kr36Crawler
from vc_tracker.multi_crawler import MultiCrawler
from vc_tracker.analyzer import FundingAnalyzer
from vc_tracker.visualizer import FundingVisualizer
from vc_tracker.utils import generate_html_report

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'{DATA_DIR}/vc_tracker.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


def crawl_command(args):
    """执行抓取命令"""
    logger.info("=" * 50)
    logger.info("开始抓取数据")
    logger.info("=" * 50)
    
    crawler = Kr36Crawler()
    data = crawler.run(pages=args.pages)
    
    logger.info(f"抓取完成！共获取 {len(data)} 条融资新闻")
    
    if data and args.verbose:
        print("\n前5条数据预览:")
        for i, item in enumerate(data[:5], 1):
            print(f"\n{i}. {item.get('title', 'N/A')}")
            print(f"   公司: {item.get('company', 'N/A')}")
            print(f"   赛道: {item.get('sector', 'N/A')}")
            print(f"   金额: {item.get('amount', 'N/A')}")


def crawl_multi_command(args):
    """执行多站点抓取命令"""
    logger.info("=" * 60)
    logger.info("开始多站点数据抓取")
    logger.info("=" * 60)
    
    multi_crawler = MultiCrawler()
    
    # 解析要抓取的站点
    sources = []
    all_sources = ['paulgraham', 'hackernews', 'samaltman', 'fredwilson', 'benedictevans']
    if args.all:
        sources = list(all_sources)
    else:
        if args.pg:
            sources.append('paulgraham')
        if args.hn:
            sources.append('hackernews')
        if args.sa:
            sources.append('samaltman')
        if args.fw:
            sources.append('fredwilson')
        if args.be:
            sources.append('benedictevans')

    if not sources:
        logger.warning("未选择任何数据源，默认抓取所有")
        sources = list(all_sources)

    print(f"\n将抓取以下数据源: {', '.join(sources)}")

    # 执行抓取
    if len(sources) == len(all_sources):
        news_items = multi_crawler.crawl_all(max_items_per_site=args.max_items)
    else:
        news_items = multi_crawler.crawl_selected(sources, max_items_per_site=args.max_items)
    
    # 保存数据
    multi_crawler.save_data()
    
    logger.info(f"\n抓取完成！共获取 {len(news_items)} 条新闻")
    
    if news_items and args.verbose:
        print("\n前10条新闻预览:")
        for i, item in enumerate(news_items[:10], 1):
            print(f"\n{i}. [{item.source}] {item.title[:70]}...")
            if item.url:
                print(f"   链接: {item.url}")


def list_command(args):
    """列出所有标题"""
    logger.info("加载新闻列表...")
    
    multi_crawler = MultiCrawler()
    
    # 尝试加载已有数据
    multi_crawler.load_data()
    
    # 如果没有数据或需要刷新
    if not multi_crawler.data or args.refresh:
        print("正在刷新数据...")
        multi_crawler.crawl_all(max_items_per_site=30)
        multi_crawler.save_data()
    
    # 过滤数据源
    titles = multi_crawler.get_title_list(
        limit=args.limit,
        source=args.source
    )
    
    if not titles:
        print("\n没有找到新闻数据")
        return
    
    # 显示标题列表
    print("\n" + "=" * 80)
    print(f"新闻标题列表 (共 {len(titles)} 条)")
    print("=" * 80)
    
    for i, item in enumerate(titles, 1):
        source_tag = f"[{item['source']}]"
        title = item['title'][:60] + "..." if len(item['title']) > 60 else item['title']
        sector = f"({item['sector']})" if item.get('sector') else ''
        
        print(f"\n{i:3d}. {source_tag:15s} {title:65s} {sector}")
        print(f"     URL: {item['url'][:70]}...")
    
    print("\n" + "=" * 80)
    print(f"显示 {len(titles)} 条新闻")
    print("=" * 80)


def refresh_command(args):
    """刷新所有数据"""
    logger.info("=" * 60)
    logger.info("开始刷新所有数据源")
    logger.info("=" * 60)
    
    multi_crawler = MultiCrawler()
    
    # 解析要刷新的站点
    all_sources = ['paulgraham', 'hackernews', 'samaltman', 'fredwilson', 'benedictevans']
    sources = []
    if args.all:
        sources = list(all_sources)
    else:
        if args.pg or not any([args.hn, args.sa, args.fw, args.be]):
            sources.append('paulgraham')
        if args.hn:
            sources.append('hackernews')
        if args.sa:
            sources.append('samaltman')
        if args.fw:
            sources.append('fredwilson')
        if args.be:
            sources.append('benedictevans')

    print(f"\n正在刷新数据源: {', '.join(sources)}")

    if len(sources) == len(all_sources):
        news_items = multi_crawler.refresh(max_items_per_site=args.max_items)
    else:
        news_items = multi_crawler.crawl_selected(sources, max_items_per_site=args.max_items)
    
    multi_crawler.save_data()
    
    print(f"\n✅ 刷新完成！共获取 {len(news_items)} 条新闻")
    print(f"数据已保存到: {DATA_DIR}/multi_source_news.json")
    
    # 显示统计
    source_counts = {}
    for item in news_items:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
    
    print("\n各数据源统计:")
    for source, count in sorted(source_counts.items()):
        print(f"  - {source}: {count} 条")


def analyze_command(args):
    """执行分析命令"""
    logger.info("=" * 50)
    logger.info("开始分析数据")
    logger.info("=" * 50)
    
    analyzer = FundingAnalyzer()
    
    if analyzer.df.empty:
        logger.error("没有找到数据，请先运行抓取命令")
        print("错误：没有找到数据，请先运行: python main.py crawl")
        return
    
    # 赛道热度分析
    print("\n" + "=" * 50)
    print("赛道热度分析")
    print("=" * 50)
    sector_data = analyzer.analyze_sector_heat(top_n=args.top_n)
    print(sector_data.to_string(index=False))
    
    # 融资轮次分布
    print("\n" + "=" * 50)
    print("融资轮次分布")
    print("=" * 50)
    round_data = analyzer.analyze_round_distribution()
    print(round_data.to_string(index=False))
    
    # 时间趋势
    print("\n" + "=" * 50)
    print("最近30天时间趋势")
    print("=" * 50)
    trend_data = analyzer.analyze_time_trend(days=30)
    if not trend_data.empty:
        print(trend_data.to_string(index=False))
    
    # 最活跃投资机构
    print("\n" + "=" * 50)
    print("最活跃投资机构 TOP 10")
    print("=" * 50)
    investor_data = analyzer.analyze_top_investors(top_n=10)
    print(investor_data.to_string(index=False))
    
    # 数据摘要
    print("\n" + "=" * 50)
    print("数据摘要")
    print("=" * 50)
    summary = analyzer.generate_summary()
    for key, value in summary.items():
        print(f"{key}: {value}")


def visualize_command(args):
    """执行可视化命令"""
    logger.info("=" * 50)
    logger.info("开始生成可视化图表")
    logger.info("=" * 50)
    
    analyzer = FundingAnalyzer()
    
    if analyzer.df.empty:
        logger.error("没有找到数据，请先运行抓取命令")
        print("错误：没有找到数据，请先运行: python main.py crawl")
        return
    
    visualizer = FundingVisualizer()
    visualizer.generate_all_visualizations(analyzer)
    
    print(f"\n图表已生成，保存在: {CHARTS_DIR}")
    print("包含以下图表:")
    print("  - sector_heatmap.png (赛道热度分析)")
    print("  - round_distribution.png (轮次分布)")
    print("  - time_trend.png (时间趋势)")
    print("  - sector_treemap.html (交互式赛道分布)")
    print("  - interactive_dashboard.html (综合仪表板)")
    print("  - wordcloud.png (关键词云)")


def report_command(args):
    """执行报告生成命令"""
    logger.info("=" * 50)
    logger.info("开始生成分析报告")
    logger.info("=" * 50)
    
    analyzer = FundingAnalyzer()
    
    if analyzer.df.empty:
        logger.error("没有找到数据，请先运行抓取命令")
        print("错误：没有找到数据，请先运行: python main.py crawl")
        return
    
    # 先生成可视化图表
    visualizer = FundingVisualizer()
    visualizer.generate_all_visualizations(analyzer)
    
    # 生成HTML报告
    if args.format == 'html':
        report_path = generate_html_report(analyzer)
        if report_path:
            print(f"\nHTML报告已生成: {report_path}")
            print(f"请用浏览器打开查看完整报告")
    
    # 导出CSV
    csv_path = f"{DATA_DIR}/funding_data.csv"
    analyzer.export_to_csv(csv_path)
    print(f"CSV数据已导出: {csv_path}")


def all_command(args):
    """执行完整的抓取-分析-可视化流程"""
    logger.info("=" * 50)
    logger.info("开始完整流程")
    logger.info("=" * 50)
    
    # 1. 抓取数据
    print("\n【步骤1/4】抓取数据...")
    crawl_args = argparse.Namespace(pages=args.pages, verbose=True)
    crawl_command(crawl_args)
    
    # 2. 分析数据
    print("\n【步骤2/4】分析数据...")
    analyze_args = argparse.Namespace(top_n=15)
    analyze_command(analyze_args)
    
    # 3. 生成可视化
    print("\n【步骤3/4】生成可视化图表...")
    visualize_args = argparse.Namespace()
    visualize_command(visualize_args)
    
    # 4. 生成报告
    print("\n【步骤4/4】生成报告...")
    report_args = argparse.Namespace(format='html')
    report_command(report_args)
    
    print("\n" + "=" * 50)
    print("全部完成！")
    print("=" * 50)
    print(f"数据文件: {DATA_DIR}/funding_data.json")
    print(f"图表目录: {CHARTS_DIR}")
    print(f"报告文件: {REPORTS_DIR}/funding_analysis_report.html")


def multi_all_command(args):
    """执行多站点的完整流程"""
    logger.info("=" * 60)
    logger.info("开始多站点完整流程")
    logger.info("=" * 60)
    
    # 1. 抓取所有站点
    print("\n【步骤1/3】抓取多站点数据...")
    refresh_args = argparse.Namespace(
        all=True, pg=False, hn=False, sa=False, fw=False, be=False,
        max_items=args.max_items
    )
    refresh_command(refresh_args)
    
    # 2. 列出标题
    print("\n【步骤2/3】显示标题列表...")
    list_args = argparse.Namespace(
        refresh=False, limit=20, source=None
    )
    list_command(list_args)
    
    # 3. 生成多源报告
    print("\n【步骤3/3】生成多源分析报告...")
    multi_crawler = MultiCrawler()
    multi_crawler.load_data()
    
    if multi_crawler.data:
        # 生成简单的统计报告
        source_counts = {}
        sector_counts = {}
        
        for item in multi_crawler.data:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
            if item.sector:
                sector_counts[item.sector] = sector_counts.get(item.sector, 0) + 1
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_news': len(multi_crawler.data),
            'source_distribution': source_counts,
            'top_sectors': sorted(sector_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        }
        
        report_path = f"{REPORTS_DIR}/multi_source_report.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n多源报告已生成: {report_path}")
        print(f"\n数据摘要:")
        print(f"  总新闻数: {report['total_news']}")
        print(f"  数据源: {len(report['source_distribution'])} 个")
        print(f"  热门赛道: {report['top_sectors'][0][0] if report['top_sectors'] else 'N/A'}")
    
    print("\n" + "=" * 60)
    print("多站点流程完成！")
    print("=" * 60)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='VC投资热度追踪器 - 多站点VC投资数据追踪工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 基础命令
  python main.py crawl --pages 5              # 抓取36kr数据
  python main.py analyze                      # 分析数据
  python main.py visualize                    # 生成可视化图表
  python main.py report --format html         # 生成HTML报告
  python main.py all --pages 10               # 执行完整流程
  
  # 多站点命令 (5个数据源)
  python main.py multi-crawl --all            # 抓取所有5个站点
  python main.py multi-crawl --pg --hn        # 抓取Paul Graham和HN
  python main.py list                         # 列出所有标题
  python main.py list --refresh               # 刷新并列出标题
  python main.py list --source hackernews     # 只列出Hacker News
  python main.py refresh --all                # 刷新所有数据源
  python main.py multi-all --max-items 20     # 执行多站点完整流程
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # ====== 基础命令 ======
    
    # crawl 命令
    crawl_parser = subparsers.add_parser('crawl', help='抓取36kr融资新闻数据')
    crawl_parser.add_argument('--pages', '-p', type=int, default=5, help='要抓取的页数')
    crawl_parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    crawl_parser.set_defaults(func=crawl_command)
    
    # analyze 命令
    analyze_parser = subparsers.add_parser('analyze', help='分析融资数据')
    analyze_parser.add_argument('--top-n', '-n', type=int, default=15, help='显示前N个赛道')
    analyze_parser.set_defaults(func=analyze_command)
    
    # visualize 命令
    visualize_parser = subparsers.add_parser('visualize', help='生成可视化图表')
    visualize_parser.set_defaults(func=visualize_command)
    
    # report 命令
    report_parser = subparsers.add_parser('report', help='生成分析报告')
    report_parser.add_argument('--format', '-f', choices=['html', 'json'], default='html')
    report_parser.set_defaults(func=report_command)
    
    # all 命令
    all_parser = subparsers.add_parser('all', help='执行完整流程（36kr单站点）')
    all_parser.add_argument('--pages', '-p', type=int, default=5)
    all_parser.set_defaults(func=all_command)
    
    # ====== 多站点命令 (新增) ======
    
    # multi-crawl 命令
    multi_crawl_parser = subparsers.add_parser('multi-crawl', help='抓取多站点数据')
    multi_crawl_parser.add_argument('--all', '-a', action='store_true', help='抓取所有站点')
    multi_crawl_parser.add_argument('--pg', action='store_true', help='抓取Paul Graham文章')
    multi_crawl_parser.add_argument('--hn', action='store_true', help='抓取Hacker News')
    multi_crawl_parser.add_argument('--sa', action='store_true', help='抓取Sam Altman博客')
    multi_crawl_parser.add_argument('--fw', action='store_true', help='抓取Fred Wilson (AVC)')
    multi_crawl_parser.add_argument('--be', action='store_true', help='抓取Benedict Evans')
    multi_crawl_parser.add_argument('--max-items', '-m', type=int, default=30, help='每站点最大条目数')
    multi_crawl_parser.add_argument('--verbose', '-v', action='store_true', help='显示详细信息')
    multi_crawl_parser.set_defaults(func=crawl_multi_command)
    
    # list 命令
    list_parser = subparsers.add_parser('list', help='列出所有新闻标题')
    list_parser.add_argument('--refresh', '-r', action='store_true', help='刷新数据后列出')
    list_parser.add_argument('--limit', '-l', type=int, default=50, help='显示条数限制')
    list_parser.add_argument('--source', '-s', type=str, help='按数据源过滤 (paulgraham/hackernews/samaltman/fredwilson/benedictevans)')
    list_parser.set_defaults(func=list_command)
    
    # refresh 命令
    refresh_parser = subparsers.add_parser('refresh', help='刷新所有数据源')
    refresh_parser.add_argument('--all', '-a', action='store_true', help='刷新所有站点')
    refresh_parser.add_argument('--pg', action='store_true', help='刷新Paul Graham')
    refresh_parser.add_argument('--hn', action='store_true', help='刷新Hacker News')
    refresh_parser.add_argument('--sa', action='store_true', help='刷新Sam Altman博客')
    refresh_parser.add_argument('--fw', action='store_true', help='刷新Fred Wilson (AVC)')
    refresh_parser.add_argument('--be', action='store_true', help='刷新Benedict Evans')
    refresh_parser.add_argument('--max-items', '-m', type=int, default=30)
    refresh_parser.set_defaults(func=refresh_command)
    
    # multi-all 命令
    multi_all_parser = subparsers.add_parser('multi-all', help='执行多站点完整流程')
    multi_all_parser.add_argument('--max-items', '-m', type=int, default=30)
    multi_all_parser.set_defaults(func=multi_all_command)
    
    # 解析参数
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    
    # 执行对应的命令
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\n\n操作已取消")
        sys.exit(0)
    except Exception as e:
        logger.error(f"执行出错: {e}")
        raise


if __name__ == '__main__':
    main()
