# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 数据分析模块
用于分析融资数据的热度和趋势
"""

import json
import logging
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from typing import List, Dict, Tuple

import pandas as pd
import numpy as np

from config.settings import DATA_DIR, ANALYSIS_CONFIG, SECTOR_KEYWORDS, EXCHANGE_RATES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FundingAnalyzer:
    """融资数据分析师"""
    
    def __init__(self, data_path: str = None):
        """
        初始化分析器
        
        Args:
            data_path: 数据文件路径，如果为None则使用默认路径
        """
        self.data_path = data_path or f"{DATA_DIR}/funding_data.json"
        self.data = []
        self.df = None
        self._load_data()
        
    def _load_data(self):
        """加载数据"""
        try:
            with open(self.data_path, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            self.df = pd.DataFrame(self.data)
            logger.info(f"成功加载 {len(self.data)} 条数据")
        except FileNotFoundError:
            logger.error(f"数据文件不存在: {self.data_path}")
            self.data = []
            self.df = pd.DataFrame()
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            self.data = []
            self.df = pd.DataFrame()
    
    def analyze_sector_heat(self, top_n: int = None) -> pd.DataFrame:
        """
        分析各赛道的热度
        
        Args:
            top_n: 显示前N个赛道，默认使用配置文件中的值
            
        Returns:
            赛道热度DataFrame
        """
        if self.df.empty:
            logger.warning("没有数据可供分析")
            return pd.DataFrame()
        
        top_n = top_n or ANALYSIS_CONFIG['top_n_sectors']
        
        # 统计各赛道的融资事件数量
        sector_counts = self.df['sector'].value_counts().head(top_n)
        
        # 统计各赛道的融资金额（需要解析金额）
        sector_amounts = defaultdict(float)
        
        for _, row in self.df.iterrows():
            sector = row.get('sector', '其他')
            amount = self._parse_amount(row.get('amount', ''))
            sector_amounts[sector] += amount
        
        # 创建分析结果
        results = []
        for sector in sector_counts.index:
            results.append({
                'sector': sector,
                'funding_count': sector_counts[sector],
                'total_amount': round(sector_amounts.get(sector, 0), 2),
                'avg_amount': round(sector_amounts.get(sector, 0) / sector_counts[sector], 2) if sector_counts[sector] > 0 else 0
            })
        
        result_df = pd.DataFrame(results)
        
        # 计算热度指数（综合融资数量和金额）
        if not result_df.empty:
            max_count = result_df['funding_count'].max()
            max_amount = result_df['total_amount'].max()
            
            result_df['heat_index'] = (
                0.6 * result_df['funding_count'] / max_count +
                0.4 * result_df['total_amount'] / max_amount
            ) * 100
            
            result_df = result_df.sort_values('heat_index', ascending=False)
        
        return result_df
    
    def _parse_amount(self, amount_str: str) -> float:
        """
        解析融资金额字符串，转换为数值（单位：万元）
        """
        if not amount_str:
            return 0
        
        amount_str = str(amount_str)
        
        # 处理模糊金额
        if '数千万' in amount_str:
            return 5000  # 默认5000万
        elif '数百万' in amount_str:
            return 500   # 默认500万
        elif '数亿' in amount_str:
            return 50000  # 默认5亿
        elif '数十亿' in amount_str:
            return 500000  # 默认50亿
        elif '近百亿' in amount_str or '超百亿' in amount_str:
            return 100000  # 100亿
        
        # 提取数值和单位
        import re
        pattern = r'([\d\.]+)\s*([万亿]?)'
        match = re.search(pattern, amount_str)
        
        if not match:
            return 0
        
        value = float(match.group(1))
        unit = match.group(2)
        
        # 判断货币单位
        if '美元' in amount_str or '美金' in amount_str or '$' in amount_str:
            value *= EXCHANGE_RATES.get('USD', 7.2)
        elif '欧元' in amount_str or '€' in amount_str:
            value *= EXCHANGE_RATES.get('EUR', 7.8)
        
        # 转换单位
        if unit == '万':
            return value
        elif unit == '亿':
            return value * 10000
        elif unit == '万亿':
            return value * 100000000
        else:
            # 没有单位，假设是元，转换为万元
            return value / 10000
    
    def analyze_round_distribution(self) -> pd.DataFrame:
        """
        分析融资轮次分布
        """
        if self.df.empty:
            return pd.DataFrame()
        
        round_counts = self.df['round'].value_counts()
        
        results = []
        for round_name, count in round_counts.items():
            results.append({
                'round': round_name or '未披露',
                'count': count,
                'percentage': round(count / len(self.df) * 100, 2)
            })
        
        return pd.DataFrame(results)
    
    def analyze_time_trend(self, days: int = 30) -> pd.DataFrame:
        """
        分析时间趋势
        
        Args:
            days: 分析最近多少天的数据
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # 解析发布时间
        self.df['publish_date'] = pd.to_datetime(self.df['publish_time'], errors='coerce')
        
        # 过滤最近N天的数据
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        recent_df = self.df[
            (self.df['publish_date'] >= start_date) & 
            (self.df['publish_date'] <= end_date)
        ]
        
        if recent_df.empty:
            logger.warning(f"最近 {days} 天内没有数据")
            return pd.DataFrame()
        
        # 按日期统计
        daily_stats = recent_df.groupby(recent_df['publish_date'].dt.date).agg({
            'title': 'count',
            'amount': lambda x: sum(self._parse_amount(str(a)) for a in x)
        }).reset_index()
        
        daily_stats.columns = ['date', 'funding_count', 'total_amount']
        
        return daily_stats
    
    def analyze_top_companies(self, top_n: int = None) -> pd.DataFrame:
        """
        分析最活跃的公司（融资次数最多）
        """
        if self.df.empty:
            return pd.DataFrame()
        
        top_n = top_n or ANALYSIS_CONFIG['top_n_companies']
        
        # 按公司统计
        company_stats = self.df.groupby('company').agg({
            'title': 'count',
            'amount': lambda x: sum(self._parse_amount(str(a)) for a in x)
        }).reset_index()
        
        company_stats.columns = ['company', 'funding_count', 'total_amount']
        company_stats = company_stats.sort_values('funding_count', ascending=False).head(top_n)
        
        return company_stats
    
    def analyze_top_investors(self, top_n: int = 20) -> pd.DataFrame:
        """
        分析最活跃的投资机构
        """
        if self.df.empty:
            return pd.DataFrame()
        
        # 统计所有投资方
        investor_counter = Counter()
        investor_amounts = defaultdict(float)
        
        for _, row in self.df.iterrows():
            investors = row.get('investors', [])
            amount = self._parse_amount(str(row.get('amount', '')))
            
            if isinstance(investors, list):
                for investor in investors:
                    if investor:
                        investor_counter[investor] += 1
                        investor_amounts[investor] += amount
        
        # 创建结果
        results = []
        for investor, count in investor_counter.most_common(top_n):
            results.append({
                'investor': investor,
                'investment_count': count,
                'total_amount': round(investor_amounts[investor], 2)
            })
        
        return pd.DataFrame(results)
    
    def generate_summary(self) -> Dict:
        """
        生成数据摘要
        """
        if self.df.empty:
            return {'error': '没有数据'}
        
        total_funding = sum(self._parse_amount(str(amount)) for amount in self.df['amount'] if amount)
        
        summary = {
            'total_news': len(self.df),
            'total_funding_amount': round(total_funding, 2),
            'date_range': {
                'start': self.df['publish_time'].min() if 'publish_time' in self.df.columns else None,
                'end': self.df['publish_time'].max() if 'publish_time' in self.df.columns else None
            },
            'top_sector': self.analyze_sector_heat(1).iloc[0]['sector'] if not self.analyze_sector_heat(1).empty else None,
            'most_active_round': self.analyze_round_distribution().iloc[0]['round'] if not self.analyze_round_distribution().empty else None,
        }
        
        return summary
    
    def export_to_csv(self, filepath: str = None):
        """
        导出数据到CSV
        """
        if self.df.empty:
            logger.warning("没有数据可供导出")
            return
        
        filepath = filepath or f"{DATA_DIR}/funding_data.csv"
        try:
            self.df.to_csv(filepath, index=False, encoding='utf-8-sig')
            logger.info(f"数据已导出到: {filepath}")
        except Exception as e:
            logger.error(f"导出数据失败: {e}")


if __name__ == '__main__':
    # 测试分析器
    analyzer = FundingAnalyzer()
    
    if not analyzer.df.empty:
        print("\n=== 赛道热度分析 ===")
        sector_heat = analyzer.analyze_sector_heat()
        print(sector_heat.to_string(index=False))
        
        print("\n=== 融资轮次分布 ===")
        round_dist = analyzer.analyze_round_distribution()
        print(round_dist.to_string(index=False))
        
        print("\n=== 数据摘要 ===")
        summary = analyzer.generate_summary()
        print(json.dumps(summary, ensure_ascii=False, indent=2))
