# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 多站点爬虫模块（新版）
支持：Paul Graham, Hacker News, Sam Altman, Fred Wilson (AVC), Benedict Evans
"""

import json
import os
import re
import time
import random
import logging
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass, asdict

import requests
import feedparser
from bs4 import BeautifulSoup

from config.settings import SECTOR_KEYWORDS, DATA_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class NewsItem:
    """新闻条目数据类"""
    title: str
    url: str
    source: str
    publish_time: str
    summary: str = ''
    company: str = ''
    amount: str = ''
    round: str = ''
    sector: str = ''
    investors: List[str] = None  # type: ignore
    crawl_time: str = ''
    unique_id: str = ''
    
    MAX_AGE_DAYS = None  # 不限制数据保留时间
    
    def __post_init__(self):
        if self.investors is None:
            self.investors = []
        if not self.crawl_time:
            self.crawl_time = datetime.now().isoformat()
        if not self.unique_id:
            content = f"{self.title}_{self.url}_{self.source}"
            self.unique_id = hashlib.md5(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def get_publish_datetime(self) -> Optional[datetime]:
        """解析发布时间为datetime对象"""
        try:
            return datetime.fromisoformat(self.publish_time.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        for fmt in (
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d',
            '%Y/%m/%d %H:%M:%S',
        ):
            try:
                return datetime.strptime(self.publish_time, fmt)
            except (ValueError, TypeError):
                continue
        return None
    
    def is_within_date_range(self, days: Optional[int] = None) -> bool:
        """检查新闻是否在指定时间范围内（days=None 表示不限制）"""
        if days is None:
            return True

        pub_dt = self.get_publish_datetime()
        if not pub_dt:
            return True

        if pub_dt.tzinfo:
            pub_dt = pub_dt.replace(tzinfo=None)

        cutoff_date = datetime.now() - timedelta(days=days)
        return pub_dt >= cutoff_date


class BaseCrawler:
    """爬虫基类"""
    
    def __init__(self, source_name: str, base_url: str, delay: float = 0.5):
        self.source_name = source_name
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)
        
    def _random_delay(self):
        """随机延迟"""
        time.sleep(self.delay + random.uniform(0, 1))
        
    def _make_request(self, url: str, retries: int = 0, timeout: int = 15) -> Optional[requests.Response]:
        """发送HTTP请求，支持重试"""
        try:
            self._random_delay()
            response = self.session.get(url, timeout=timeout, allow_redirects=True)
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            if retries < 3:
                logger.warning(f"[{self.source_name}] 请求失败，正在重试 ({retries + 1}/3): {url}")
                time.sleep(2 ** retries)
                return self._make_request(url, retries + 1)
            else:
                logger.error(f"[{self.source_name}] 请求失败: {url}, 错误: {e}")
                return None
    
    def parse_relative_time(self, time_str: str) -> Optional[datetime]:
        """解析相对时间（如'2 hours ago', '1 day ago'）为绝对时间"""
        if not time_str:
            return None
        
        time_str = time_str.lower().strip()
        now = datetime.now()
        
        patterns = [
            (r'(\d+)\s*minute', 'minutes'),
            (r'(\d+)\s*hour', 'hours'),
            (r'(\d+)\s*day', 'days'),
            (r'(\d+)\s*week', 'weeks'),
            (r'(\d+)\s*month', 'months'),
        ]
        
        for pattern, unit in patterns:
            match = re.search(pattern, time_str)
            if match:
                value = int(match.group(1))
                if unit == 'minutes':
                    return now - timedelta(minutes=value)
                elif unit == 'hours':
                    return now - timedelta(hours=value)
                elif unit == 'days':
                    return now - timedelta(days=value)
                elif unit == 'weeks':
                    return now - timedelta(weeks=value)
                elif unit == 'months':
                    return now - timedelta(days=value * 30)
        
        return None
    
    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取新闻，子类需要实现"""
        raise NotImplementedError


class PaulGrahamCrawler(BaseCrawler):
    """Paul Graham 文章爬虫 - 抓取创业与投资相关文章"""
    
    def __init__(self):
        super().__init__('Paul Graham', 'https://paulgraham.com', 0.3)
    
    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取Paul Graham文章列表"""
        logger.info(f"[{self.source_name}] 开始抓取文章")
        news_items = []
        
        try:
            url = 'https://paulgraham.com/articles.html'
            response = self._make_request(url)
            
            if not response:
                logger.error(f"[{self.source_name}] 无法获取页面")
                return news_items
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Paul Graham文章页面是一个表格结构，每行包含文章链接
            # 文章链接通常在 <font> 标签内的 <a> 标签
            links = soup.find_all('a', href=re.compile(r'\.html$'))
            
            logger.info(f"[{self.source_name}] 找到 {len(links)} 个文章链接")
            
            for link in links[:max_items]:
                try:
                    title = link.get_text(strip=True)
                    href = link.get('href', '')
                    
                    if not title or not href:
                        continue
                    
                    # 跳过非文章链接
                    skip_pages = ['index.html', 'articles.html', 'books.html', 'nac.html', 'faq.html', 'filter.html']
                    if href in skip_pages:
                        continue
                    
                    full_url = urljoin(self.base_url, href)
                    
                    # Paul Graham的文章通常没有明确的发布日期，我们使用当前时间作为近似
                    # 实际上他的文章很少，每条都很有价值
                    news_item = NewsItem(
                        title=title,
                        url=full_url,
                        source=self.source_name,
                        publish_time=datetime.now().isoformat(),
                        summary='Paul Graham关于创业和投资的经典文章',
                        sector='Startups & Investment'
                    )
                    news_items.append(news_item)
                    logger.info(f"[{self.source_name}] 添加文章: {title[:50]}...")
                    
                except Exception as e:
                    logger.debug(f"[{self.source_name}] 解析文章时出错: {e}")
                    continue
                
                if len(news_items) >= max_items:
                    break
            
        except Exception as e:
            logger.error(f"[{self.source_name}] 抓取失败: {e}")
        
        logger.info(f"[{self.source_name}] 共抓取到 {len(news_items)} 篇文章")
        return news_items


class HackerNewsCrawler(BaseCrawler):
    """Hacker News 爬虫 - 抓取最新热门文章"""
    
    def __init__(self):
        super().__init__('Hacker News', 'https://news.ycombinator.com', 0.3)
    
    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取Hacker News最新文章"""
        logger.info(f"[{self.source_name}] 开始抓取新闻")
        news_items = []
        
        try:
            url = 'https://news.ycombinator.com/'
            response = self._make_request(url)
            
            if not response:
                logger.error(f"[{self.source_name}] 无法获取页面")
                return news_items
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # HN的结构：每个文章有class="titleline"的span
            titleline_elements = soup.find_all('span', class_='titleline')
            
            logger.info(f"[{self.source_name}] 找到 {len(titleline_elements)} 篇文章")
            
            for idx, titleline in enumerate(titleline_elements):
                try:
                    link_elem = titleline.find('a')
                    if not link_elem:
                        continue
                    
                    title = link_elem.get_text(strip=True)
                    link = link_elem.get('href', '')
                    
                    if link and not link.startswith('http'):
                        link = urljoin(self.base_url, link)
                    
                    # 获取发布时间
                    subtext_row = titleline.find_parent('tr')
                    if subtext_row:
                        subtext_row = subtext_row.find_next_sibling('tr')
                    
                    pub_date = None
                    if subtext_row:
                        age_elem = subtext_row.find('span', class_='age')
                        if age_elem:
                            time_str = age_elem.get('title', '')
                            if time_str:
                                try:
                                    pub_date = datetime.fromisoformat(time_str.replace(' ', 'T'))
                                except (ValueError, TypeError):
                                    pass
                            
                            if not pub_date:
                                age_text = age_elem.get_text(strip=True)
                                pub_date = self.parse_relative_time(age_text)
                    
                    if not pub_date:
                        pub_date = datetime.now()

                    sector = self._identify_sector_from_title(title)
                    
                    news_item = NewsItem(
                        title=title,
                        url=link,
                        source=self.source_name,
                        publish_time=pub_date.isoformat(),
                        sector=sector
                    )
                    news_items.append(news_item)
                    logger.info(f"[{self.source_name}] 添加文章: {title[:50]}...")
                    
                except Exception as e:
                    logger.debug(f"[{self.source_name}] 解析文章时出错: {e}")
                    continue
                
                if len(news_items) >= max_items:
                    break
            
        except Exception as e:
            logger.error(f"[{self.source_name}] 抓取失败: {e}")
        
        logger.info(f"[{self.source_name}] 共抓取到 {len(news_items)} 条新闻")
        return news_items
    
    def _identify_sector_from_title(self, title: str) -> str:
        """从标题识别领域"""
        title_lower = title.lower()
        keywords = {
            'AI': ['ai', 'artificial intelligence', 'machine learning', 'ml', 'chatgpt', 'llm'],
            'Programming': ['programming', 'coding', 'developer', 'software', 'github'],
            'Startup': ['startup', 'founder', 'venture', 'funding', 'series', 'investor'],
            'Tech': ['tech', 'technology', 'app', 'web', 'cloud'],
        }
        
        for sector, words in keywords.items():
            if any(word in title_lower for word in words):
                return sector
        
        return 'General'


class RSSCrawler(BaseCrawler):
    """RSS/Atom 通用爬虫基类（使用 feedparser）"""

    def __init__(self, source_name: str, base_url: str, feed_url: str,
                 delay: float = 1.5):
        super().__init__(source_name, base_url, delay)
        self.feed_url = feed_url

    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        logger.info(f"[{self.source_name}] 开始抓取 feed: {self.feed_url}")
        news_items = []

        try:
            response = self._make_request(self.feed_url)
            if not response:
                logger.error(f"[{self.source_name}] 无法获取 feed")
                return news_items

            feed = feedparser.parse(response.content)

            if feed.bozo and not feed.entries:
                logger.error(f"[{self.source_name}] feed 解析失败: {feed.bozo_exception}")
                return news_items

            logger.info(f"[{self.source_name}] 找到 {len(feed.entries)} 篇文章")

            for entry in feed.entries[:max_items]:
                try:
                    item = self._parse_entry(entry)
                    if item:
                        news_items.append(item)
                        logger.info(f"[{self.source_name}] 添加文章: {item.title[:50]}...")
                except Exception as e:
                    logger.debug(f"[{self.source_name}] 解析条目时出错: {e}")
                    continue

                if len(news_items) >= max_items:
                    break

        except Exception as e:
            logger.error(f"[{self.source_name}] 抓取失败: {e}")

        logger.info(f"[{self.source_name}] 共抓取到 {len(news_items)} 篇文章")
        return news_items

    def _parse_entry(self, entry) -> Optional[NewsItem]:
        """解析 feedparser 条目"""
        title = entry.get('title', '').strip()
        if not title:
            return None

        url = entry.get('link', '')
        if not url:
            return None

        # 解析发布时间
        pub_time = None
        time_struct = entry.get('published_parsed') or entry.get('updated_parsed')
        if time_struct:
            try:
                pub_time = datetime(*time_struct[:6])
            except (TypeError, ValueError):
                pass

        # 获取摘要（去除 HTML 标签）
        summary_raw = entry.get('summary', '') or entry.get('description', '')
        summary = re.sub(r'<[^>]+>', '', summary_raw)[:200].strip()

        return NewsItem(
            title=title,
            url=url,
            source=self.source_name,
            publish_time=pub_time.isoformat() if pub_time else datetime.now().isoformat(),
            summary=summary,
            sector='VC & Tech',
        )



class SamAltmanCrawler(BaseCrawler):
    """Sam Altman 博客爬虫 - 网页版"""

    def __init__(self):
        super().__init__('Sam Altman', 'https://blog.samaltman.com', 0.3)

    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取Sam Altman博客文章"""
        logger.info(f"[{self.source_name}] 开始抓取文章")
        news_items = []
        seen_titles = set()

        try:
            # 抓取多页
            page = 1
            while len(news_items) < max_items and page <= 5:
                if page == 1:
                    url = 'https://blog.samaltman.com/'
                else:
                    url = f'https://blog.samaltman.com/?page={page}'

                response = self._make_request(url)
                if not response:
                    break

                soup = BeautifulSoup(response.text, 'lxml')

                # Sam Altman博客结构：每篇文章在 <article class="post"> 中
                # 标题在 <h2><a href="...">标题</a></h2>
                articles = soup.find_all('article', class_='post')
                
                logger.info(f"[{self.source_name}] 第{page}页找到 {len(articles)} 篇文章")

                for article in articles:
                    if len(news_items) >= max_items:
                        break

                    try:
                        # 获取标题
                        title_elem = article.find('h2')
                        if not title_elem:
                            continue
                            
                        link_elem = title_elem.find('a', href=True)
                        if not link_elem:
                            continue

                        title = link_elem.get_text(strip=True)
                        href = str(link_elem.get('href', ''))
                        
                        if not title or not href or title in seen_titles:
                            continue
                            
                        seen_titles.add(title)
                        full_url = urljoin(self.base_url, href)

                        news_item = NewsItem(
                            title=title,
                            url=full_url,
                            source=self.source_name,
                            publish_time=datetime.now().isoformat(),
                            summary='Sam Altman关于创业、AI和科技的观点',
                            sector='AI & Startups'
                        )
                        news_items.append(news_item)
                        logger.info(f"[{self.source_name}] 添加文章: {title[:50]}...")

                    except Exception as e:
                        logger.debug(f"[{self.source_name}] 解析文章时出错: {e}")
                        continue

                # 检查是否有下一页
                next_link = soup.find('a', text=re.compile(r'Next', re.I))
                if not next_link:
                    # 尝试其他方式找到下一页
                    pagination = soup.find('div', class_=re.compile(r'pagination', re.I))
                    if pagination:
                        next_link = pagination.find('a', text=re.compile(r'[>›]|next', re.I))

                if not next_link or len(articles) == 0:
                    break

                page += 1

        except Exception as e:
            logger.error(f"[{self.source_name}] 抓取失败: {e}")

        logger.info(f"[{self.source_name}] 共抓取到 {len(news_items)} 篇文章")
        return news_items


class FredWilsonCrawler(RSSCrawler):
    """Fred Wilson (AVC) 博客爬虫"""

    def __init__(self):
        super().__init__(
            source_name='Fred Wilson',
            base_url='https://avc.xyz',
            feed_url='https://avc.xyz/feed',
        )


class BenedictEvansCrawler(RSSCrawler):
    """Benedict Evans 博客爬虫"""

    def __init__(self):
        super().__init__(
            source_name='Benedict Evans',
            base_url='https://www.ben-evans.com',
            feed_url='https://www.ben-evans.com/benedictevans?format=rss',
        )


class MultiCrawler:
    """多站点爬虫管理器"""
    
    DATA_RETENTION_DAYS = None  # 不限制
    
    def __init__(self):
        # 5个数据源：经典博客 + Hacker News
        self.crawlers = {
            'paulgraham': PaulGrahamCrawler(),
            'hackernews': HackerNewsCrawler(),
            'samaltman': SamAltmanCrawler(),
            'fredwilson': FredWilsonCrawler(),
            'benedictevans': BenedictEvansCrawler(),
        }
        self.data = []
        self.title_cache = set()
    
    def filter_by_date(self, items: List[NewsItem], days: Optional[int] = None) -> List[NewsItem]:
        """过滤指定时间范围内的数据"""
        if days is None:
            days = self.DATA_RETENTION_DAYS
        
        filtered = []
        removed_count = 0
        
        for item in items:
            if item.is_within_date_range(days):
                filtered.append(item)
            else:
                removed_count += 1
        
        if removed_count > 0:
            logger.info(f"过滤了 {removed_count} 条超过 {days} 天的旧数据")
        
        return filtered
    
    def crawl_all(self, max_items_per_site: int = 30) -> List[NewsItem]:
        """并行抓取所有站点 - 优化版本"""
        logger.info("=" * 60)
        logger.info("开始并行抓取所有站点")
        logger.info("=" * 60)

        all_news = []
        self.title_cache.clear()
        
        # 使用线程池并行爬取
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        def crawl_single_source(source_name, crawler):
            """爬取单个源"""
            try:
                start_time = time.time()
                news_items = crawler.crawl(max_items=max_items_per_site)
                elapsed = time.time() - start_time
                logger.info(f"[{source_name}] 爬取完成，耗时 {elapsed:.1f}s，获取 {len(news_items)} 条")
                return source_name, news_items
            except Exception as e:
                logger.error(f"[{source_name}] 抓取异常: {e}")
                return source_name, []
        
        # 并行执行所有爬虫
        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_source = {
                executor.submit(crawl_single_source, source, crawler): source 
                for source, crawler in self.crawlers.items()
            }
            
            for future in as_completed(future_to_source):
                source_name, news_items = future.result()
                
                source_count = 0
                for item in news_items:
                    title_key = item.title.lower().strip()
                    if title_key not in self.title_cache and len(title_key) > 5:
                        self.title_cache.add(title_key)
                        all_news.append(item)
                        source_count += 1
                
                logger.info(f"[{source_name}] 去重后保留 {source_count} 条")
        
        # 按发布时间排序（最新的在前）
        random.shuffle(all_news)

        self.data = all_news
        logger.info(f"总计抓取 {len(all_news)} 条新闻")
        
        # 显示数据时间范围
        if all_news:
            dates = [item.get_publish_datetime() for item in all_news if item.get_publish_datetime()]
            if dates:
                dates = [d for d in dates if d]
                if dates:
                    oldest = min(dates)
                    newest = max(dates)
                    logger.info(f"数据时间范围: {oldest.strftime('%Y-%m-%d')} 至 {newest.strftime('%Y-%m-%d')}")
        
        return all_news
    
    def crawl_selected(self, sources: List[str], max_items_per_site: int = 30) -> List[NewsItem]:
        """只抓取选定的站点"""
        logger.info(f"开始抓取选定站点: {sources}")
        
        all_news = []
        self.title_cache.clear()
        
        for source in sources:
            if source in self.crawlers:
                try:
                    crawler = self.crawlers[source]
                    news_items = crawler.crawl(max_items=max_items_per_site)

                    for item in news_items:
                        title_key = item.title.lower().strip()
                        if title_key not in self.title_cache and len(title_key) > 5:
                            self.title_cache.add(title_key)
                            all_news.append(item)
                    
                except Exception as e:
                    logger.error(f"[{source}] 抓取异常: {e}")
            else:
                logger.warning(f"未知的数据源: {source}")
        
        random.shuffle(all_news)
        self.data = all_news

        return all_news
    
    def get_title_list(self, limit: Optional[int] = None, source: Optional[str] = None) -> List[Dict]:
        """获取title列表"""
        items = self.data if not source else [item for item in self.data if item.source == source]
        
        if limit:
            items = items[:limit]
        
        return [
            {
                'id': item.unique_id,
                'title': item.title,
                'source': item.source,
                'url': item.url,
                'publish_time': item.publish_time,
                'sector': item.sector,
                'company': item.company,
                'amount': item.amount,
            }
            for item in items
        ]
    
    def refresh(self, max_items_per_site: int = 30) -> List[NewsItem]:
        """刷新数据（自动清理过期数据）"""
        logger.info("正在刷新数据...")
        
        self.load_data()
        
        new_items = self.crawl_all(max_items_per_site)
        
        existing_urls = {item.url for item in self.data}
        merged_items = list(self.data)
        
        for item in new_items:
            if item.url not in existing_urls:
                merged_items.append(item)
        
        seen_urls = set()
        unique_items = []
        for item in merged_items:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)

        self.data = unique_items
        self.title_cache = {item.title.lower().strip() for item in self.data}
        
        logger.info(f"刷新完成，共 {len(self.data)} 条新闻")
        
        return self.data
    
    def save_data(self, filepath: str = None):
        """保存数据到文件（原子写入）"""
        filepath = filepath or f"{DATA_DIR}/multi_source_news.json"
        tmp_path = filepath + '.tmp'
        try:
            data = [item.to_dict() for item in self.data]
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, filepath)

            if self.data:
                dates = [item.get_publish_datetime() for item in self.data if item.get_publish_datetime()]
                dates = [d for d in dates if d]
                if dates:
                    oldest = min(dates)
                    newest = max(dates)
                    logger.info(f"数据时间范围: {oldest.strftime('%Y-%m-%d')} 至 {newest.strftime('%Y-%m-%d')}")

            logger.info(f"数据已保存: {filepath} (共 {len(self.data)} 条)")
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
    
    def load_data(self, filepath: str = None):
        """从文件加载数据"""
        filepath = filepath or f"{DATA_DIR}/multi_source_news.json"
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            all_items = []
            for item_data in data:
                try:
                    news_item = NewsItem(**item_data)
                    all_items.append(news_item)
                except Exception as e:
                    logger.warning(f"加载数据项失败: {e}")
                    continue
            
            self.data = all_items
            self.title_cache = {item.title.lower().strip() for item in self.data}

            logger.info(f"从文件加载了 {len(self.data)} 条数据")
            
            if self.data:
                dates = [item.get_publish_datetime() for item in self.data if item.get_publish_datetime()]
                dates = [d for d in dates if d]
                if dates:
                    oldest = min(dates)
                    newest = max(dates)
                    logger.info(f"当前数据时间范围: {oldest.strftime('%Y-%m-%d')} 至 {newest.strftime('%Y-%m-%d')}")
                    
        except FileNotFoundError:
            logger.warning(f"数据文件不存在: {filepath}")
            self.data = []
            self.title_cache = set()
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.data = []
            self.title_cache = set()


if __name__ == '__main__':
    multi_crawler = MultiCrawler()
    
    print("\n测试抓取所有站点:")
    news = multi_crawler.crawl_all(max_items_per_site=10)
    
    print(f"\n总计获取 {len(news)} 条新闻")
    print("\n前5条:")
    for item in multi_crawler.get_title_list(limit=5):
        pub_dt = datetime.fromisoformat(item['publish_time'])
        print(f"[{item['source']}] ({pub_dt.strftime('%Y-%m-%d')}) {item['title'][:60]}...")
