# -*- coding: utf-8 -*-
"""
集成测试 — 真实网络请求
默认跳过，设置 RUN_INTEGRATION=1 运行
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vc_tracker.multi_crawler import MultiCrawler

pytestmark = pytest.mark.integration

skip_unless_integration = pytest.mark.skipif(
    os.environ.get("RUN_INTEGRATION") != "1",
    reason="Set RUN_INTEGRATION=1 to run integration tests",
)


@skip_unless_integration
def test_crawl_all():
    """测试抓取所有站点"""
    multi_crawler = MultiCrawler()
    news = multi_crawler.crawl_all(max_items_per_site=3)

    assert isinstance(news, list)
    print(f"\n总计获取 {len(news)} 条新闻")

    for i, item in enumerate(news[:10], 1):
        print(f"\n{i}. [{item.source}]")
        print(f"   标题: {item.title[:60]}...")
        print(f"   链接: {item.url[:60]}...")

    if news:
        multi_crawler.save_data()

        source_counts = {}
        for item in news:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1
        for source, count in sorted(source_counts.items()):
            print(f"  {source}: {count} 条")
