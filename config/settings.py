# -*- coding: utf-8 -*-
"""
VC投资热度追踪器 - 配置文件
"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, 'data')
OUTPUT_DIR = os.path.join(BASE_DIR, 'output')
CHARTS_DIR = os.path.join(OUTPUT_DIR, 'charts')
REPORTS_DIR = os.path.join(OUTPUT_DIR, 'reports')

# 确保目录存在
for directory in [DATA_DIR, CHARTS_DIR, REPORTS_DIR]:
    os.makedirs(directory, exist_ok=True)

# 36kr爬虫配置
KR36_CONFIG = {
    'base_url': 'https://36kr.com',
    'search_url': 'https://36kr.com/search/articles/融资',
    'funding_url': 'https://36kr.com/information/web_fundings',
    'headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    },
    'delay': 2,  # 请求间隔（秒）
    'timeout': 30,
    'max_pages': 10,
    'max_retries': 3
}

# 赛道关键词映射（用于识别行业/赛道）
SECTOR_KEYWORDS = {
    '人工智能': ['AI', '人工智能', 'AIGC', '大模型', '机器学习', '深度学习', 'NLP', '计算机视觉', 'CV'],
    '生物医药': ['生物医药', '医疗', '医药', '医疗器械', '生物科技', '生命科学', '诊断', '基因', '疫苗'],
    '新能源': ['新能源', '光伏', '储能', '锂电池', '氢能', '风电', '太阳能', '电动汽车'],
    '半导体': ['半导体', '芯片', '集成电路', 'IC', '晶圆', '光刻', 'EDA', '封装测试'],
    '企业服务': ['企业服务', 'SaaS', '云原生', '协同办公', 'CRM', 'ERP', 'RPA', '低代码'],
    '消费零售': ['消费', '零售', '电商', '新零售', '品牌', '餐饮', '食品饮料', '美妆'],
    '金融科技': ['金融', '金融科技', 'FinTech', '保险', '支付', '区块链', '数字货币', '财富'],
    '智能制造': ['智能制造', '工业互联网', '机器人', '自动化', '3D打印', '工业软件'],
    '物联网': ['物联网', 'IoT', '传感器', '智能硬件', '智能家居', '车联网'],
    '航空航天': ['航天', '航空', '卫星', '火箭', '商业航天', '无人机'],
    '教育': ['教育', '在线教育', '职业教育', '素质教育', 'K12'],
    '游戏': ['游戏', '电竞', '游戏开发', '元宇宙', 'VR', 'AR', '虚拟现实'],
    '物流': ['物流', '供应链', '仓储', '配送', '快递', '冷链'],
    '文娱': ['文娱', '影视', '音乐', '文娱传媒', '内容', '社交'],
}

# 融资轮次标准化映射
ROUND_MAPPING = {
    '种子': '种子轮',
    '天使': '天使轮',
    'Pre-A': 'Pre-A轮',
    'A': 'A轮',
    'A+': 'A+轮',
    'B': 'B轮',
    'B+': 'B+轮',
    'C': 'C轮',
    'C+': 'C+轮',
    'D': 'D轮',
    'D+': 'D+轮',
    'E': 'E轮',
    'F': 'F轮',
    'Pre-IPO': 'Pre-IPO',
    'IPO': 'IPO',
    '战略': '战略投资',
    '并购': '并购',
}

# 汇率配置（目标货币：人民币）
EXCHANGE_RATES = {
    'USD': 7.2,
    'EUR': 7.8,
}

# 分析配置
ANALYSIS_CONFIG = {
    'top_n_sectors': 15,  # 显示前N个热门赛道
    'top_n_companies': 20,  # 显示前N个活跃公司
    'min_funding_amount': 0,  # 最小融资金额（万元）
    'chart_style': 'seaborn',
    'color_palette': 'viridis'
}

# 可视化配置
CHART_CONFIG = {
    'figure_size': (12, 8),
    'dpi': 300,
    'font_family': 'SimHei',  # Linux/Mac可能需要调整
    'font_size': 12,
    'save_format': ['png', 'html']  # 输出格式
}
