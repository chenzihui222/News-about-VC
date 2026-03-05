#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新的多站点爬虫
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vc_tracker.multi_crawler import MultiCrawler

def test_crawlers():
    """测试所有爬虫"""
    print("=" * 60)
    print("测试新的多站点爬虫")
    print("数据源: Paul Graham, Hacker News, Product Hunt, IT桔子")
    print("=" * 60)
    
    multi_crawler = MultiCrawler()
    
    # 测试抓取所有站点（每个站点只抓3条）
    print("\n开始测试抓取（每站点3条）...")
    news = multi_crawler.crawl_all(max_items_per_site=3)
    
    print(f"\n总计获取 {len(news)} 条新闻\n")
    
    # 显示结果
    if news:
        print("=" * 60)
        print("抓取结果预览:")
        print("=" * 60)
        
        for i, item in enumerate(news[:10], 1):
            print(f"\n{i}. [{item.source}]")
            print(f"   标题: {item.title[:60]}...")
            print(f"   链接: {item.url[:60]}...")
            if item.sector:
                print(f"   赛道: {item.sector}")
            if item.company:
                print(f"   公司: {item.company}")
        
        # 保存数据
        multi_crawler.save_data()
        print(f"\n\n数据已保存到: data/multi_source_news.json")
        
        # 显示统计
        print("\n" + "=" * 60)
        print("数据源统计:")
        print("=" * 60)
        source_counts = {}
        for item in news:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
        
        for source, count in sorted(source_counts.items()):
            print(f"  {source}: {count} 条")
    else:
        print("\n警告: 没有抓取到任何数据")
        print("可能原因:")
        print("  1. 网络连接问题")
        print("  2. 目标网站结构变化")
        print("  3. 被反爬虫机制拦截")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)

if __name__ == '__main__':
    test_crawlers()
