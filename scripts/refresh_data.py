#!/usr/bin/env python3
"""
VC雷达 - 数据刷新脚本
运行此脚本可重新爬取所有5个站点的数据并更新到静态文件
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vc_tracker.multi_crawler import MultiCrawler
import json
from datetime import datetime

def refresh_vc_radar():
    print("=" * 60)
    print("🔄 VC雷达 - 数据刷新")
    print("=" * 60)
    print(f"\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    mc = MultiCrawler()
    
    # 爬取所有5个站点 - 尽可能多地获取数据
    print("\n正在爬取5个数据源(最大化获取)...")
    items = mc.crawl_all(max_items_per_site=50)
    
    # 保存数据
    mc.save_data()
    
    # 同时更新静态文件
    static_data_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'data.json')
    with open(static_data_path, 'w', encoding='utf-8') as f:
        json.dump([item.__dict__ for item in items], f, ensure_ascii=False, indent=2)
    
    print("\n" + "=" * 60)
    print(f"✅ 刷新完成！共 {len(items)} 条新闻")
    print("=" * 60)
    
    # 统计
    source_counts = {}
    for item in items:
        source_counts[item.source] = source_counts.get(item.source, 0) + 1
    
    print("\n📊 数据来源:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source:20s}: {count:3d} 条")
    
    print(f"\n💾 数据已保存到:")
    print(f"  - data/multi_source_news.json")
    print(f"  - static/data.json")
    print(f"\n更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    return len(items)

if __name__ == '__main__':
    refresh_vc_radar()
