# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 爬虫模块
用于从36kr抓取融资新闻数据
"""

import json
import re
import time
import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from config.settings import KR36_CONFIG, SECTOR_KEYWORDS, ROUND_MAPPING, DATA_DIR

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Kr36Crawler:
    """36kr融资新闻爬虫"""
    
    def __init__(self):
        self.config = KR36_CONFIG
        self.headers = self.config['headers']
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        self.data = []
        
    def _random_delay(self):
        """随机延迟，避免被封"""
        delay = self.config['delay'] + random.uniform(0, 1)
        time.sleep(delay)
        
    def _make_request(self, url: str, retries: int = 0) -> Optional[requests.Response]:
        """
        发送HTTP请求，支持重试
        """
        try:
            self._random_delay()
            response = self.session.get(
                url, 
                timeout=self.config['timeout'],
                allow_redirects=True
            )
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response
        except requests.RequestException as e:
            if retries < self.config['max_retries']:
                logger.warning(f"请求失败，正在重试 ({retries + 1}/{self.config['max_retries']}): {url}")
                time.sleep(2 ** retries)  # 指数退避
                return self._make_request(url, retries + 1)
            else:
                logger.error(f"请求失败: {url}, 错误: {e}")
                return None
    
    def _extract_funding_info(self, title: str, content: str) -> Dict:
        """
        从标题和内容中提取融资信息
        """
        info = {
            'company': '',
            'amount': '',
            'round': '',
            'sector': '',
            'investors': []
        }
        
        # 提取公司名（通常在"完成"、"获得"等词之前）
        company_patterns = [
            r'^(.*?)完成',
            r'^(.*?)获',
            r'^(.*?)宣布',
            r'^(.*?)获投',
        ]
        for pattern in company_patterns:
            match = re.search(pattern, title)
            if match:
                info['company'] = match.group(1).strip()
                break
        
        # 提取融资金额
        amount_patterns = [
            r'([\d\.]+)\s*([万亿]?)(?:美元|人民币|元|美金|欧元)',
            r'([\d\.]+)\s*([万亿]?)元',
            r'数千万',
            r'数百万',
            r'数亿',
            r'近\s*([\d\.]+)\s*([万亿]?)',
            r'超\s*([\d\.]+)\s*([万亿]?)',
        ]
        for pattern in amount_patterns:
            match = re.search(pattern, title)
            if match:
                info['amount'] = match.group(0).strip()
                break
        
        # 提取融资轮次
        for round_key in ROUND_MAPPING.keys():
            if round_key in title:
                info['round'] = ROUND_MAPPING[round_key]
                break
        
        # 识别赛道
        info['sector'] = self._identify_sector(title + ' ' + content)
        
        # 提取投资方（在"由"、"投"等词之后）
        investor_patterns = [
            r'由(.*?)投资',
            r'由(.*?)领投',
            r'由(.*?)跟投',
            r'投资方包括(.*?)等',
        ]
        for pattern in investor_patterns:
            match = re.search(pattern, title + ' ' + content)
            if match:
                investors_text = match.group(1)
                # 分割多个投资方
                info['investors'] = [i.strip() for i in re.split(r'[、,，和与及]', investors_text) if i.strip()]
                break
        
        return info
    
    def _identify_sector(self, text: str) -> str:
        """
        根据关键词识别赛道
        """
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
            # 返回得分最高的赛道
            return max(sector_scores.items(), key=lambda x: x[1])[0]
        
        return '其他'
    
    def crawl_funding_news(self, pages: int = 5) -> List[Dict]:
        """
        抓取融资新闻列表
        
        Args:
            pages: 要抓取的页数
            
        Returns:
            融资新闻列表
        """
        logger.info(f"开始抓取融资新闻，计划抓取 {pages} 页")
        
        all_news = []
        
        # 36kr的融资新闻接口
        # 由于36kr使用了动态渲染，我们需要使用API或搜索页面
        # 这里提供两种策略
        
        # 策略1: 通过搜索API获取融资相关新闻
        try:
            news_list = self._crawl_via_search(pages)
            all_news.extend(news_list)
        except Exception as e:
            logger.error(f"搜索抓取失败: {e}")
            
        # 策略2: 如果有特定的融资频道URL，可以尝试直接访问
        # 但由于网站结构可能变化，这里作为备选
        
        logger.info(f"共抓取到 {len(all_news)} 条融资新闻")
        return all_news
    
    def _crawl_via_search(self, pages: int = 5) -> List[Dict]:
        """
        通过搜索抓取融资新闻
        """
        news_list = []
        
        # 36kr的搜索API
        # 注意：这个URL可能需要根据实际网站结构调整
        search_api = "https://gateway.36kr.com/api/mis/nav/search/fts"
        
        for page in tqdm(range(1, pages + 1), desc="抓取进度"):
            try:
                payload = {
                    "page": page,
                    "per_page": 20,
                    "sort": "date",
                    "searchWord": "融资",
                    "searchType": "article"
                }
                
                response = self.session.post(
                    search_api,
                    json=payload,
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    data = response.json()
                    items = data.get('data', {}).get('itemList', [])
                    
                    for item in items:
                        news = self._parse_news_item(item)
                        if news:
                            news_list.append(news)
                else:
                    logger.warning(f"API返回状态码: {response.status_code}")
                    
            except Exception as e:
                logger.error(f"抓取第 {page} 页时出错: {e}")
                
        return news_list
    
    def _parse_news_item(self, item: Dict) -> Optional[Dict]:
        """
        解析新闻条目
        """
        try:
            title = item.get('widgetTitle', '') or item.get('title', '')
            summary = item.get('summary', '') or item.get('content', '')
            url = item.get('widgetLink', '') or item.get('route', '')
            publish_time = item.get('publishTime', '')
            
            if not title:
                return None
            
            # 提取融资信息
            funding_info = self._extract_funding_info(title, summary)
            
            news = {
                'title': title,
                'summary': summary,
                'url': urljoin(self.config['base_url'], url) if url and not url.startswith('http') else url,
                'publish_time': self._parse_time(publish_time),
                'company': funding_info['company'],
                'amount': funding_info['amount'],
                'round': funding_info['round'],
                'sector': funding_info['sector'],
                'investors': funding_info['investors'],
                'source': '36kr',
                'crawl_time': datetime.now().isoformat()
            }
            
            return news
            
        except Exception as e:
            logger.error(f"解析新闻条目时出错: {e}")
            return None
    
    def _parse_time(self, time_str: str) -> str:
        """
        解析时间字符串
        """
        if not time_str:
            return datetime.now().isoformat()
        
        try:
            # 尝试多种时间格式
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%dT%H:%M:%S',
                '%Y-%m-%d',
                '%Y/%m/%d %H:%M:%S',
            ]
            
            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    return dt.isoformat()
                except (ValueError, TypeError):
                    continue
            
            # 如果是时间戳
            if isinstance(time_str, (int, float)):
                return datetime.fromtimestamp(time_str).isoformat()
                
        except Exception as e:
            logger.warning(f"无法解析时间: {time_str}")
            
        return datetime.now().isoformat()
    
    def crawl_article_detail(self, url: str) -> Dict:
        """
        抓取文章详情
        """
        try:
            response = self._make_request(url)
            if not response:
                return {}
            
            soup = BeautifulSoup(response.text, 'lxml')
            
            # 提取文章内容
            content_selectors = [
                'article',
                '.article-content',
                '.article-detail',
                '[class*="content"]',
            ]
            
            content = ''
            for selector in content_selectors:
                element = soup.select_one(selector)
                if element:
                    content = element.get_text(strip=True)
                    break
            
            return {
                'content': content,
                'full_text': soup.get_text(strip=True)
            }
            
        except Exception as e:
            logger.error(f"抓取文章详情失败: {url}, 错误: {e}")
            return {}
    
    def save_data(self, filename: str = 'funding_data.json'):
        """
        保存数据到JSON文件
        """
        filepath = f"{DATA_DIR}/{filename}"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
            logger.info(f"数据已保存到: {filepath}")
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
    
    def run(self, pages: int = 5):
        """
        运行爬虫
        """
        self.data = self.crawl_funding_news(pages)
        self.save_data()
        return self.data


if __name__ == '__main__':
    # 测试爬虫
    crawler = Kr36Crawler()
    data = crawler.run(pages=2)
    print(f"抓取完成，共 {len(data)} 条数据")
    if data:
        print("\n示例数据:")
        print(json.dumps(data[0], ensure_ascii=False, indent=2))
