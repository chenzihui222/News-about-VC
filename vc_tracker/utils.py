# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 工具函数模块
"""

import os
import json
import logging
from datetime import datetime
from typing import List, Dict, Any

import pandas as pd

from config.settings import REPORTS_DIR, DATA_DIR

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_html_report(analyzer, output_path: str = None) -> str:
    """
    生成HTML格式的分析报告
    
    Args:
        analyzer: FundingAnalyzer实例
        output_path: 输出文件路径
        
    Returns:
        报告文件路径
    """
    if analyzer.df.empty:
        logger.error("没有数据可供生成报告")
        return None
    
    # 获取分析数据
    sector_data = analyzer.analyze_sector_heat()
    round_data = analyzer.analyze_round_distribution()
    summary = analyzer.generate_summary()
    
    # 生成HTML
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VC投资热度分析报告</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Microsoft YaHei', sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1200px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 10px;
                margin-bottom: 30px;
                text-align: center;
            }}
            .header h1 {{
                margin: 0;
                font-size: 2.5em;
            }}
            .header p {{
                margin: 10px 0 0 0;
                opacity: 0.9;
            }}
            .summary-cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin-bottom: 30px;
            }}
            .card {{
                background: white;
                padding: 25px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                text-align: center;
            }}
            .card h3 {{
                margin: 0 0 10px 0;
                color: #666;
                font-size: 0.9em;
                text-transform: uppercase;
            }}
            .card .value {{
                font-size: 2em;
                font-weight: bold;
                color: #667eea;
            }}
            .section {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                margin-bottom: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .section h2 {{
                color: #333;
                border-bottom: 3px solid #667eea;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th, td {{
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }}
            th {{
                background-color: #f8f9fa;
                font-weight: bold;
                color: #555;
            }}
            tr:hover {{
                background-color: #f8f9fa;
            }}
            .sector-tag {{
                display: inline-block;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85em;
                font-weight: 500;
            }}
            .trend-up {{ color: #28a745; }}
            .trend-down {{ color: #dc3545; }}
            .chart-container {{
                text-align: center;
                margin: 20px 0;
            }}
            .chart-container img {{
                max-width: 100%;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                color: #666;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>VC投资热度分析报告</h1>
            <p>基于36kr融资新闻数据分析 | 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="summary-cards">
            <div class="card">
                <h3>总融资事件</h3>
                <div class="value">{summary.get('total_news', 0)}</div>
            </div>
            <div class="card">
                <h3>总融资金额</h3>
                <div class="value">{summary.get('total_funding_amount', 0):,.0f}万</div>
            </div>
            <div class="card">
                <h3>最热门赛道</h3>
                <div class="value">{summary.get('top_sector', 'N/A')}</div>
            </div>
            <div class="card">
                <h3>最活跃轮次</h3>
                <div class="value">{summary.get('most_active_round', 'N/A')}</div>
            </div>
        </div>
        
        <div class="section">
            <h2>赛道热度排名</h2>
            <table>
                <thead>
                    <tr>
                        <th>排名</th>
                        <th>赛道</th>
                        <th>融资事件</th>
                        <th>总金额(万元)</th>
                        <th>平均金额(万元)</th>
                        <th>热度指数</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # 添加赛道数据行
    for idx, row in sector_data.iterrows():
        html_content += f"""
                    <tr>
                        <td>{idx + 1}</td>
                        <td><span class="sector-tag">{row['sector']}</span></td>
                        <td>{int(row['funding_count'])}</td>
                        <td>{row['total_amount']:,.2f}</td>
                        <td>{row['avg_amount']:,.2f}</td>
                        <td>{row['heat_index']:.2f}</td>
                    </tr>
        """
    
    html_content += """
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>融资轮次分布</h2>
            <table>
                <thead>
                    <tr>
                        <th>轮次</th>
                        <th>事件数量</th>
                        <th>占比</th>
                    </tr>
                </thead>
                <tbody>
    """
    
    # 添加轮次数据行
    for idx, row in round_data.iterrows():
        html_content += f"""
                    <tr>
                        <td>{row['round']}</td>
                        <td>{int(row['count'])}</td>
                        <td>{row['percentage']}%</td>
                    </tr>
        """
    
    html_content += f"""
                </tbody>
            </table>
        </div>
        
        <div class="section">
            <h2>可视化图表</h2>
            <div class="chart-container">
                <h3>赛道热度分析</h3>
                <img src="charts/sector_heatmap.png" alt="赛道热度图">
            </div>
            <div class="chart-container">
                <h3>融资轮次分布</h3>
                <img src="charts/round_distribution.png" alt="轮次分布图">
            </div>
        </div>
        
        <div class="footer">
            <p>本报告由VC投资热度追踪器自动生成 | 数据来源: 36kr.com</p>
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
    </body>
    </html>
    """
    
    # 保存报告
    output_path = output_path or f"{REPORTS_DIR}/funding_analysis_report.html"
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML报告已生成: {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"生成HTML报告失败: {e}")
        return None


def format_number(num: float, decimals: int = 2) -> str:
    """
    格式化数字显示
    """
    if num >= 100000000:
        return f"{num/100000000:.{decimals}f}亿"
    elif num >= 10000:
        return f"{num/10000:.{decimals}f}万"
    else:
        return f"{num:.{decimals}f}"


def save_json(data: Any, filepath: str):
    """
    保存数据为JSON文件
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"数据已保存到: {filepath}")
    except Exception as e:
        logger.error(f"保存JSON失败: {e}")


def load_json(filepath: str) -> Any:
    """
    加载JSON文件
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"加载JSON失败: {e}")
        return None


if __name__ == '__main__':
    # 测试工具函数
    from analyzer import FundingAnalyzer
    
    analyzer = FundingAnalyzer()
    if not analyzer.df.empty:
        report_path = generate_html_report(analyzer)
        print(f"报告已生成: {report_path}")
    else:
        print("没有数据，无法生成报告")
