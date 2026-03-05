# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 可视化模块
用于生成各种图表和报告
"""

import os
import logging
from datetime import datetime
from typing import List, Dict

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from wordcloud import WordCloud
import jieba

import sys
sys.path.append('..')
from config.settings import CHARTS_DIR, REPORTS_DIR, CHART_CONFIG, ANALYSIS_CONFIG

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False


class FundingVisualizer:
    """融资数据可视化器"""
    
    def __init__(self):
        self.chart_dir = CHARTS_DIR
        self.report_dir = REPORTS_DIR
        
        # 设置样式
        sns.set_style(CHART_CONFIG.get('chart_style', 'seaborn'))
        self.color_palette = CHART_CONFIG.get('color_palette', 'viridis')
        
    def plot_sector_heatmap(self, sector_data: pd.DataFrame, save: bool = True) -> str:
        """
        绘制赛道热度柱状图
        
        Args:
            sector_data: 赛道数据DataFrame
            save: 是否保存图片
            
        Returns:
            图片保存路径
        """
        if sector_data.empty:
            logger.warning("没有数据可供可视化")
            return None
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))
        
        # 融资数量
        colors1 = plt.cm.viridis(range(0, len(sector_data) * 10, 10))
        ax1.barh(sector_data['sector'], sector_data['funding_count'], color=colors1)
        ax1.set_xlabel('融资事件数量', fontsize=12)
        ax1.set_title('各赛道融资事件数量', fontsize=14, fontweight='bold')
        ax1.invert_yaxis()
        
        # 在柱状图上添加数值
        for i, v in enumerate(sector_data['funding_count']):
            ax1.text(v + 0.5, i, str(int(v)), va='center', fontsize=10)
        
        # 热度指数
        colors2 = plt.cm.plasma(range(0, len(sector_data) * 10, 10))
        ax2.barh(sector_data['sector'], sector_data['heat_index'], color=colors2)
        ax2.set_xlabel('热度指数', fontsize=12)
        ax2.set_title('各赛道投资热度指数', fontsize=14, fontweight='bold')
        ax2.invert_yaxis()
        
        for i, v in enumerate(sector_data['heat_index']):
            ax2.text(v + 1, i, f'{v:.1f}', va='center', fontsize=10)
        
        plt.tight_layout()
        
        if save:
            filepath = f"{self.chart_dir}/sector_heatmap.png"
            plt.savefig(filepath, dpi=CHART_CONFIG['dpi'], bbox_inches='tight')
            logger.info(f"图表已保存: {filepath}")
            plt.close()
            return filepath
        else:
            plt.show()
            return None
    
    def plot_round_distribution(self, round_data: pd.DataFrame, save: bool = True) -> str:
        """
        绘制融资轮次饼图
        """
        if round_data.empty:
            return None
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 7))
        
        # 饼图
        colors = plt.cm.Set3(range(len(round_data)))
        ax1.pie(
            round_data['count'], 
            labels=round_data['round'], 
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        ax1.set_title('融资轮次分布', fontsize=14, fontweight='bold')
        
        # 柱状图
        colors_bar = plt.cm.Paired(range(len(round_data)))
        bars = ax2.bar(round_data['round'], round_data['count'], color=colors_bar)
        ax2.set_xlabel('融资轮次', fontsize=12)
        ax2.set_ylabel('事件数量', fontsize=12)
        ax2.set_title('各轮次融资数量', fontsize=14, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45)
        
        # 在柱状图上添加数值
        for bar in bars:
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height,
                    f'{int(height)}',
                    ha='center', va='bottom', fontsize=10)
        
        plt.tight_layout()
        
        if save:
            filepath = f"{self.chart_dir}/round_distribution.png"
            plt.savefig(filepath, dpi=CHART_CONFIG['dpi'], bbox_inches='tight')
            logger.info(f"图表已保存: {filepath}")
            plt.close()
            return filepath
        else:
            plt.show()
            return None
    
    def plot_time_trend(self, trend_data: pd.DataFrame, save: bool = True) -> str:
        """
        绘制时间趋势图
        """
        if trend_data.empty:
            return None
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        # 融资数量趋势
        ax1.plot(trend_data['date'], trend_data['funding_count'], 
                marker='o', linewidth=2, markersize=6, color='#2E86AB')
        ax1.fill_between(trend_data['date'], trend_data['funding_count'], 
                         alpha=0.3, color='#2E86AB')
        ax1.set_xlabel('日期', fontsize=12)
        ax1.set_ylabel('融资事件数量', fontsize=12)
        ax1.set_title('每日融资事件数量趋势', fontsize=14, fontweight='bold')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # 融资金额趋势
        ax2.plot(trend_data['date'], trend_data['total_amount'], 
                marker='s', linewidth=2, markersize=6, color='#A23B72')
        ax2.fill_between(trend_data['date'], trend_data['total_amount'], 
                         alpha=0.3, color='#A23B72')
        ax2.set_xlabel('日期', fontsize=12)
        ax2.set_ylabel('融资金额（万元）', fontsize=12)
        ax2.set_title('每日融资金额趋势', fontsize=14, fontweight='bold')
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
        
        plt.tight_layout()
        
        if save:
            filepath = f"{self.chart_dir}/time_trend.png"
            plt.savefig(filepath, dpi=CHART_CONFIG['dpi'], bbox_inches='tight')
            logger.info(f"图表已保存: {filepath}")
            plt.close()
            return filepath
        else:
            plt.show()
            return None
    
    def plot_sector_treemap(self, sector_data: pd.DataFrame, save: bool = True) -> str:
        """
        使用Plotly绘制赛道矩形树图（交互式）
        """
        if sector_data.empty:
            return None
        
        fig = px.treemap(
            sector_data,
            path=['sector'],
            values='funding_count',
            color='heat_index',
            color_continuous_scale='viridis',
            title='VC投资热度赛道分布图',
            hover_data=['total_amount', 'avg_amount']
        )
        
        fig.update_layout(
            width=1000,
            height=700,
            title_font_size=18
        )
        
        if save:
            filepath = f"{self.chart_dir}/sector_treemap.html"
            fig.write_html(filepath)
            logger.info(f"交互式图表已保存: {filepath}")
            return filepath
        else:
            fig.show()
            return None
    
    def plot_interactive_dashboard(self, sector_data: pd.DataFrame, 
                                   round_data: pd.DataFrame,
                                   trend_data: pd.DataFrame,
                                   save: bool = True) -> str:
        """
        创建交互式仪表板
        """
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=('赛道热度排名', '融资轮次分布', '时间趋势', '融资金额占比'),
            specs=[[{'type': 'bar'}, {'type': 'pie'}],
                   [{'type': 'scatter'}, {'type': 'pie'}]]
        )
        
        # 赛道热度
        if not sector_data.empty:
            fig.add_trace(
                go.Bar(x=sector_data['sector'], y=sector_data['heat_index'],
                       name='热度指数', marker_color='viridis'),
                row=1, col=1
            )
        
        # 轮次分布
        if not round_data.empty:
            fig.add_trace(
                go.Pie(labels=round_data['round'], values=round_data['count'],
                       name='轮次分布'),
                row=1, col=2
            )
        
        # 时间趋势
        if not trend_data.empty:
            fig.add_trace(
                go.Scatter(x=trend_data['date'], y=trend_data['funding_count'],
                          mode='lines+markers', name='每日融资数',
                          line=dict(color='blue')),
                row=2, col=1
            )
        
        # 赛道金额占比
        if not sector_data.empty:
            fig.add_trace(
                go.Pie(labels=sector_data['sector'], values=sector_data['total_amount'],
                       name='金额占比'),
                row=2, col=2
            )
        
        fig.update_layout(
            height=900,
            showlegend=False,
            title_text="VC投资热度分析仪表板",
            title_font_size=20
        )
        
        if save:
            filepath = f"{self.chart_dir}/interactive_dashboard.html"
            fig.write_html(filepath)
            logger.info(f"交互式仪表板已保存: {filepath}")
            return filepath
        else:
            fig.show()
            return None
    
    def generate_wordcloud(self, text_data: List[str], save: bool = True) -> str:
        """
        生成词云图
        """
        if not text_data:
            return None
        
        # 合并所有文本
        all_text = ' '.join(text_data)
        
        # 使用jieba分词
        words = jieba.cut(all_text)
        word_string = ' '.join(words)
        
        # 生成词云
        wordcloud = WordCloud(
            width=1200,
            height=800,
            background_color='white',
            font_path=None,  # 系统字体
            max_words=200,
            colormap='viridis'
        ).generate(word_string)
        
        plt.figure(figsize=(15, 10))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.title('融资新闻关键词云', fontsize=16, fontweight='bold')
        
        if save:
            filepath = f"{self.chart_dir}/wordcloud.png"
            plt.savefig(filepath, dpi=CHART_CONFIG['dpi'], bbox_inches='tight')
            logger.info(f"词云图已保存: {filepath}")
            plt.close()
            return filepath
        else:
            plt.show()
            return None
    
    def generate_all_visualizations(self, analyzer):
        """
        生成所有可视化图表
        
        Args:
            analyzer: FundingAnalyzer实例
        """
        logger.info("开始生成所有可视化图表...")
        
        # 获取数据
        sector_data = analyzer.analyze_sector_heat()
        round_data = analyzer.analyze_round_distribution()
        trend_data = analyzer.analyze_time_trend(days=30)
        
        # 生成静态图表
        if not sector_data.empty:
            self.plot_sector_heatmap(sector_data)
            self.plot_sector_treemap(sector_data)
        
        if not round_data.empty:
            self.plot_round_distribution(round_data)
        
        if not trend_data.empty:
            self.plot_time_trend(trend_data)
        
        # 生成交互式仪表板
        self.plot_interactive_dashboard(sector_data, round_data, trend_data)
        
        # 生成词云
        if not analyzer.df.empty:
            titles = analyzer.df['title'].dropna().tolist()
            self.generate_wordcloud(titles)
        
        logger.info(f"所有图表已生成，保存在: {self.chart_dir}")


if __name__ == '__main__':
    # 测试可视化
    from analyzer import FundingAnalyzer
    
    analyzer = FundingAnalyzer()
    visualizer = FundingVisualizer()
    
    if not analyzer.df.empty:
        visualizer.generate_all_visualizations(analyzer)
    else:
        print("没有数据，请先运行爬虫获取数据")
