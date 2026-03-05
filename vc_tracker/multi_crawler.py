# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 多站点爬虫模块（新版）
支持：Paul Graham, Hacker News, Product Hunt, IT桔子
"""

import json
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
from bs4 import BeautifulSoup

import sys
sys.path.append('..')
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
    
    # 数据保留时间：90天（3个月）
    MAX_AGE_DAYS = 90
    
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
        except:
            try:
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%d',
                    '%Y/%m/%d %H:%M:%S',
                ]
                for fmt in formats:
                    try:
                        return datetime.strptime(self.publish_time, fmt)
                    except:
                        continue
            except:
                pass
        return None
    
    def is_within_date_range(self, days: Optional[int] = None) -> bool:
        """检查新闻是否在指定时间范围内（默认90天）"""
        if days is None:
            days = self.MAX_AGE_DAYS
        
        pub_dt = self.get_publish_datetime()
        if not pub_dt:
            return False
        
        if pub_dt.tzinfo:
            pub_dt = pub_dt.replace(tzinfo=None)
        
        cutoff_date = datetime.now() - timedelta(days=days)
        return pub_dt >= cutoff_date


class BaseCrawler:
    """爬虫基类"""
    
    def __init__(self, source_name: str, base_url: str, delay: float = 2.0):
        self.source_name = source_name
        self.base_url = base_url
        self.delay = delay
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
        }
        self.session.headers.update(self.headers)
        
    def _random_delay(self):
        """随机延迟"""
        time.sleep(self.delay + random.uniform(0, 1))
        
    def _make_request(self, url: str, retries: int = 0, timeout: int = 30) -> Optional[requests.Response]:
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
        super().__init__('Paul Graham', 'https://paulgraham.com', 1.5)
    
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
        super().__init__('Hacker News', 'https://news.ycombinator.com', 1.0)
        self.cutoff_date = datetime.now() - timedelta(days=90)
    
    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取Hacker News最新文章（只保留90天内的）"""
        logger.info(f"[{self.source_name}] 开始抓取新闻（只保留90天内）")
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
                                except:
                                    pass
                            
                            if not pub_date:
                                age_text = age_elem.get_text(strip=True)
                                pub_date = self.parse_relative_time(age_text)
                    
                    if not pub_date:
                        pub_date = datetime.now()
                    
                    # 检查是否在90天内
                    if pub_date < self.cutoff_date:
                        continue
                    
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


class ProductHuntCrawler(BaseCrawler):
    """Product Hunt 爬虫 - 使用备用RSS/API方式获取数据"""
    
    def __init__(self):
        super().__init__('Product Hunt', 'https://www.producthunt.com', 2.0)
        self.cutoff_date = datetime.now() - timedelta(days=90)
    
    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取Product Hunt热门产品（使用备用API）"""
        logger.info(f"[{self.source_name}] 开始抓取热门产品")
        news_items = []
        
        try:
            # 尝试1: 通过RSS feed获取（Product Hunt提供RSS）
            rss_items = self._crawl_via_rss(max_items)
            if rss_items:
                return rss_items
            
            # 尝试2: 通过备用数据源（TechCrunch产品相关新闻）
            backup_items = self._crawl_backup(max_items)
            if backup_items:
                return backup_items
                
        except Exception as e:
            logger.error(f"[{self.source_name}] 抓取失败: {e}")
        
        # 尝试3: 如果都失败，返回提示信息
        if not news_items:
            logger.warning(f"[{self.source_name}] 无法直接抓取，建议使用浏览器访问")
            # 返回一个提示项
            news_items.append(NewsItem(
                title="[提示] Product Hunt需要浏览器访问",
                url="https://www.producthunt.com/",
                source=self.source_name,
                publish_time=datetime.now().isoformat(),
                summary="Product Hunt使用JavaScript动态加载，建议使用浏览器直接访问查看最新产品。",
                sector='Product Launch'
            ))
        
        logger.info(f"[{self.source_name}] 共抓取到 {len(news_items)} 个产品")
        return news_items
    
    def _crawl_via_rss(self, max_items: int) -> List[NewsItem]:
        """尝试通过RSS获取"""
        news_items = []
        try:
            # Product Hunt的RSS feed
            rss_url = "https://www.producthunt.com/feed"
            response = self._make_request(rss_url)
            
            if response and 'xml' in response.headers.get('content-type', ''):
                soup = BeautifulSoup(response.text, 'xml')
                items = soup.find_all('item')[:max_items]
                
                for item in items:
                    try:
                        title = item.find('title')
                        link = item.find('link')
                        desc = item.find('description')
                        pub_date = item.find('pubDate')
                        
                        if title and link:
                            news_item = NewsItem(
                                title=f"Product: {title.get_text(strip=True)}",
                                url=link.get_text(strip=True),
                                source=self.source_name,
                                publish_time=pub_date.get_text(strip=True) if pub_date else datetime.now().isoformat(),
                                summary=desc.get_text(strip=True)[:200] if desc else 'Product Hunt热门产品',
                                sector='Product Launch'
                            )
                            news_items.append(news_item)
                    except Exception as e:
                        continue
                        
                logger.info(f"[{self.source_name}] 通过RSS获取 {len(news_items)} 条")
        except Exception as e:
            logger.debug(f"[{self.source_name}] RSS获取失败: {e}")
        
        return news_items
    
    def _crawl_backup(self, max_items: int) -> List[NewsItem]:
        """备用数据源：抓取相关科技媒体的Product Hunt报道"""
        news_items = []
        try:
            # 使用Hacker News上关于Product Hunt的讨论作为替代
            logger.info(f"[{self.source_name}] 尝试使用HN相关讨论作为补充")
            # 这部分留空，让用户知道数据来源的限制
        except Exception as e:
            logger.debug(f"[{self.source_name}] 备用方案失败: {e}")
        
        return news_items


class ItJuziCrawler(BaseCrawler):
    """IT桔子 爬虫 - 抓取中国投融资数据"""
    
    def __init__(self):
        super().__init__('IT桔子', 'https://www.itjuzi.com', 2.0)
        self.cutoff_date = datetime.now() - timedelta(days=90)
    
    def crawl(self, max_items: int = 50) -> List[NewsItem]:
        """抓取IT桔子投融资数据"""
        logger.info(f"[{self.source_name}] 开始抓取投融资数据")
        news_items = []
        
        try:
            # IT桔子有专门的投融资页面
            # 注意：IT桔子可能需要登录或有反爬机制
            url = 'https://www.itjuzi.com/investevent'
            response = self._make_request(url)
            
            if not response:
                logger.error(f"[{self.source_name}] 无法获取页面")
                # 尝试备用页面
                return self._crawl_backup(max_items)
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # IT桔子的投资事件通常在列表中
            # 尝试多种可能的选择器
            event_rows = soup.find_all(['tr', 'div', 'li'], class_=re.compile(r'event|invest|list-item', re.I))
            
            if not event_rows:
                logger.warning(f"[{self.source_name}] 未找到投资事件，尝试备用方案")
                return self._crawl_backup(max_items)
            
            for row in event_rows[:max_items]:
                try:
                    # 提取公司名
                    company_elem = row.find(['a', 'span', 'div'], class_=re.compile(r'company|name', re.I))
                    company = company_elem.get_text(strip=True) if company_elem else ''
                    
                    # 提取金额
                    amount_elem = row.find(['span', 'div'], class_=re.compile(r'amount|money', re.I))
                    amount = amount_elem.get_text(strip=True) if amount_elem else ''
                    
                    # 提取轮次
                    round_elem = row.find(['span', 'div'], class_=re.compile(r'round|stage', re.I))
                    round_str = round_elem.get_text(strip=True) if round_elem else ''
                    
                    # 提取投资方
                    investors = []
                    investor_elems = row.find_all(['a', 'span'], class_=re.compile(r'investor', re.I))
                    for inv in investor_elems:
                        investor_name = inv.get_text(strip=True)
                        if investor_name:
                            investors.append(investor_name)
                    
                    # 提取时间
                    time_elem = row.find(['span', 'div', 'time'], class_=re.compile(r'time|date', re.I))
                    pub_time = time_elem.get_text(strip=True) if time_elem else datetime.now().isoformat()
                    
                    # 提取链接
                    link_elem = row.find('a', href=True)
                    url = ''
                    if link_elem:
                        href = link_elem.get('href', '')
                        url = urljoin(self.base_url, href)
                    
                    # 提取赛道
                    sector_elem = row.find(['span', 'div'], class_=re.compile(r'industry|sector', re.I))
                    sector = sector_elem.get_text(strip=True) if sector_elem else ''
                    
                    if company:
                        news_item = NewsItem(
                            title=f"{company} {round_str}融资" if round_str else f"{company} 融资",
                            url=url,
                            source=self.source_name,
                            publish_time=pub_time if isinstance(pub_time, str) else datetime.now().isoformat(),
                            company=company,
                            amount=amount,
                            round=round_str,
                            sector=sector or self._identify_sector(company),
                            investors=investors
                        )
                        news_items.append(news_item)
                        logger.info(f"[{self.source_name}] 添加投资事件: {company} {amount}")
                    
                except Exception as e:
                    logger.debug(f"[{self.source_name}] 解析投资事件时出错: {e}")
                    continue
                
                if len(news_items) >= max_items:
                    break
            
        except Exception as e:
            logger.error(f"[{self.source_name}] 抓取失败: {e}")
            news_items = self._crawl_backup(max_items)
        
        # 如果没有抓取到数据，添加提示
        if not news_items:
            logger.warning(f"[{self.source_name}] 无法抓取数据，建议直接访问网站")
            news_items.append(NewsItem(
                title="[提示] IT桔子需要登录或反爬限制",
                url="https://www.itjuzi.com/investevent",
                source=self.source_name,
                publish_time=datetime.now().isoformat(),
                summary="IT桔子需要登录账号或有反爬虫机制，建议直接访问网站查看最新投融资数据。",
                sector='Investment'
            ))
        
        logger.info(f"[{self.source_name}] 共抓取到 {len(news_items)} 条投资数据")
        return news_items
    
    def _crawl_backup(self, max_items: int = 50) -> List[NewsItem]:
        """备用抓取方案 - 尝试其他页面"""
        logger.info(f"[{self.source_name}] 使用备用方案抓取")
        news_items = []
        
        # 尝试公司库页面
        try:
            url = 'https://www.itjuzi.com/company'
            response = self._make_request(url)
            
            if response:
                soup = BeautifulSoup(response.text, 'lxml')
                
                # 查找公司列表
                company_links = soup.find_all('a', href=re.compile(r'/company/\d+'))
                
                for link in company_links[:max_items]:
                    try:
                        company_name = link.get_text(strip=True)
                        if not company_name:
                            continue
                        
                        href = link.get('href', '')
                        if not href:
                            continue
                            
                        full_url = urljoin(self.base_url, href)
                        if not full_url:
                            continue
                        
                        news_item = NewsItem(
                            title=f"Company: {company_name}",
                            url=full_url,
                            source=self.source_name,
                            publish_time=datetime.now().isoformat(),
                            company=company_name,
                            sector='待识别'
                        )
                        news_items.append(news_item)
                        
                    except Exception as e:
                        continue
                    
                    if len(news_items) >= max_items:
                        break
        
        except Exception as e:
            logger.error(f"[{self.source_name}] 备用方案也失败: {e}")
        
        return news_items
    
    def _identify_sector(self, text: str) -> str:
        """根据关键词识别赛道"""
        text = text.lower()
        sector_scores = {}
        
        for sector, keywords in SECTOR_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword.lower() in text:
                    score += 1
            if score > 0:
                sector_scores[sector] = score
        
        if sector_scores:
            return max(sector_scores.items(), key=lambda x: x[1])[0]
        
        return '其他'


class MultiCrawler:
    """多站点爬虫管理器"""
    
    DATA_RETENTION_DAYS = 90
    
    def __init__(self):
        # 新的4个数据源
        self.crawlers = {
            'paulgraham': PaulGrahamCrawler(),
            'hackernews': HackerNewsCrawler(),
            'producthunt': ProductHuntCrawler(),
            'itjuzi': ItJuziCrawler(),
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
        """抓取所有站点（只保留90天内的数据）"""
        logger.info("=" * 60)
        logger.info(f"开始抓取所有站点（只保留最近{self.DATA_RETENTION_DAYS}天）")
        logger.info("=" * 60)
        
        all_news = []
        self.title_cache.clear()
        
        for source, crawler in self.crawlers.items():
            try:
                news_items = crawler.crawl(max_items=max_items_per_site)
                
                # 过滤90天内的数据
                filtered_items = self.filter_by_date(news_items)
                
                source_count = 0
                for item in filtered_items:
                    title_key = item.title.lower().strip()
                    if title_key not in self.title_cache and len(title_key) > 5:
                        self.title_cache.add(title_key)
                        all_news.append(item)
                        source_count += 1
                
                logger.info(f"[{source}] 抓取 {len(news_items)} 条，过滤后 {len(filtered_items)} 条，去重后 {source_count} 条")
                
            except Exception as e:
                logger.error(f"[{source}] 抓取异常: {e}")
        
        # 按发布时间排序（最新的在前）
        all_news.sort(key=lambda x: x.publish_time, reverse=True)
        
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
                    
                    filtered_items = self.filter_by_date(news_items)
                    
                    for item in filtered_items:
                        title_key = item.title.lower().strip()
                        if title_key not in self.title_cache and len(title_key) > 5:
                            self.title_cache.add(title_key)
                            all_news.append(item)
                    
                except Exception as e:
                    logger.error(f"[{source}] 抓取异常: {e}")
            else:
                logger.warning(f"未知的数据源: {source}")
        
        all_news.sort(key=lambda x: x.publish_time, reverse=True)
        self.data = all_news
        
        return all_news
    
    def get_title_list(self, limit: Optional[int] = None, source: Optional[str] = None) -> List[Dict]:
        """获取title列表"""
        valid_items = self.filter_by_date(self.data)
        
        items = valid_items if not source else [item for item in valid_items if item.source == source]
        
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
        
        self.data = self.filter_by_date(merged_items)
        
        seen_urls = set()
        unique_items = []
        for item in self.data:
            if item.url not in seen_urls:
                seen_urls.add(item.url)
                unique_items.append(item)
        
        self.data = unique_items
        self.title_cache = {item.title.lower().strip() for item in self.data}
        
        logger.info(f"刷新完成，共 {len(self.data)} 条新闻")
        
        return self.data
    
    def save_data(self, filepath: str = None):
        """保存数据到文件"""
        filepath = filepath or f"{DATA_DIR}/multi_source_news.json"
        try:
            valid_items = self.filter_by_date(self.data)
            self.data = valid_items
            
            data = [item.to_dict() for item in self.data]
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
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
            
            original_count = len(all_items)
            self.data = self.filter_by_date(all_items)
            filtered_count = original_count - len(self.data)
            
            self.title_cache = {item.title.lower().strip() for item in self.data}
            
            logger.info(f"从文件加载了 {len(self.data)} 条数据" + 
                       (f"（已过滤 {filtered_count} 条过期数据）" if filtered_count > 0 else ""))
            
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
