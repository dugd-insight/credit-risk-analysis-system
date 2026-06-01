# -*- coding: utf-8 -*-
"""
风险引擎常量配置
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
集中管理所有阈值、系数和配置参数
"""

# ─────────────────────────────────────────────
# 通用常量
# ─────────────────────────────────────────────

EPSILON = 1e-9
"""浮点数比较精度"""

MONTHS_PER_YEAR = 12.0
"""每年月数"""

# ─────────────────────────────────────────────
# file_parser.py 常量
# ─────────────────────────────────────────────

# 年份范围
YEAR_RANGE_MIN = 2015
YEAR_RANGE_MAX = 2035

# 行号上限
MAX_ROW_NUM = 99

# 期间类型识别阈值
REVENUE_RATIO_ANNUAL_THRESHOLD = 0.20
"""12月报表：本期/累计 < 此值识别为年报"""

REVENUE_RATIO_MONTHLY_THRESHOLD = 0.80
"""12月报表：本期/累计 > 此值识别为月报"""

QUARTERLY_RATIO_UPPER = 0.75
"""季报识别：ratio 上限"""

# 利润表解析
INCOME_SWAP_THRESHOLD = 1.1
"""本期不应大于累计的倍数阈值"""

# 三表勾稽校验阈值
CASH_DIFF_THRESHOLD = 0.02
"""期末现金一致性：差异率阈值"""

EQUITY_DIFF_THRESHOLD = 0.15
"""权益变动与净利润一致性：差异率阈值"""

ACCOUNTING_EQUATION_THRESHOLD = 0.03
"""会计恒等式：差异率阈值"""

CASH_PROFIT_QUALITY_THRESHOLD = 0.6
"""利润含金量：合格阈值"""

# PDF 解析
MIN_VAT_SALES_AMOUNT = 10000
"""增值税销售额最小金额"""

# ─────────────────────────────────────────────
# risk_analyzer.py 常量
# ─────────────────────────────────────────────

# 数据校验
ACCOUNTING_EQUATION_TOLERANCE = 0.05
"""会计恒等式允许误差"""

DEBT_RATIO_ERROR_THRESHOLD = 1.2
"""负债率超过总资产的倍数阈值"""

TAX_DIFF_TOLERANCE = 0.3
"""所得税差异容忍度"""

CURRENT_ASSETS_MAX_RATIO = 1.05
"""流动资产占总资产最大比例"""

COST_REVENUE_MAX_RATIO = 3
"""营业成本/收入最大倍数"""

# 假设参数
ASSUMED_FINANCING_COST = 0.05
"""假设融资成本（无利息时）"""

# 毛利率阈值
GPM_LOW = 0.15
GPM_HIGH = 0.35

# 净利率阈值
NPM_LOW = 0.03
NPM_HIGH = 0.15

# ROE 阈值
ROE_LOW = 0.05
ROE_HIGH = 0.15

# ROA 阈值
ROA_LOW = 0.02
ROA_HIGH = 0.08

# 增长率阈值
GROWTH_NEUTRAL = 0.0
GROWTH_GOOD = 0.3

# VAT 差异惩罚系数
VAT_GAP_PENALTY_FACTOR = 300

# M-Score 阈值
MSCORE_SAFE = -2.22
"""M-Score 安全阈值"""

MSCORE_DANGER = -1.78
"""M-Score 危险阈值"""

# Beneish M-Score 系数 (Beneish 1999)
BENEISH_COEFFICIENTS = {
    'intercept': -4.84,
    'dsri': 0.920,
    'gmi': 0.528,
    'aqi': 0.404,
    'sgi': 0.892,
    'depi': 0.115,
    'sgai': -0.172,
    'tata': 4.679,
    'lvgi': -0.327,
}

# 评分函数参数
CURRENT_RATIO_CAP = 15.0
"""流动比率上限（担保公司）"""

CURRENT_RATIO_CENTER = 2.0
CURRENT_RATIO_STEEPNESS = 6.0

QUICK_RATIO_CAP = 12.0
"""速动比率上限"""

QUICK_RATIO_CENTER = 1.2
QUICK_RATIO_STEEPNESS = 7.0

DEBT_RATIO_CENTER = 0.55
DEBT_RATIO_STEEPNESS = 8.0

ICR_CAP = 30.0
"""利息保障倍数上限"""

ICR_CENTER = 3.0
ICR_STEEPNESS = 5.0

CASH_RATIO_CAP = 5.0
"""现金比率上限"""

CASH_RATIO_CENTER = 0.4
CASH_RATIO_STEEPNESS = 6.0

TAX_RATE_OPTIMAL = 0.20
"""最优税率"""

TAX_RATE_PENALTY = 300
"""税率偏离惩罚系数"""

TURNOVER_STEEPNESS = 5.0
GROWTH_STEEPNESS = 10.0

# 负债率变动惩罚系数
DEBT_RATIO_CHANGE_PENALTY = 500
DEPOSIT_CHANGE_THRESHOLD = 0.3
DEPOSIT_CHANGE_PENALTY = 100

# 跨期异常检测
ASSET_DECLINE_THRESHOLD = 0.7
"""总资产下降阈值"""

ANOMALY_SCORE_INCONSISTENT = 0.4
"""收入利润方向不一致的异常分数"""

# AR/Rev 假设
ASSUMED_AR_REVENUE_RATIO = 0.1
DSRI_CAP = 3.0

# ─────────────────────────────────────────────
# 信用评级
# ─────────────────────────────────────────────

CREDIT_GRADES = [
    (90, 100, 'AAA', '建议足额授信', 'green'),
    (80,  90, 'AA',  '建议正常授信', 'green'),
    (70,  80, 'A',   '审慎授信', 'yellow'),
    (60,  70, 'BBB', '附条件授信', 'yellow'),
    (50,  60, 'BB',  '压缩授信额度', 'orange'),
    (40,  50, 'B',   '建议拒绝或要求强担保', 'red'),
    (0,   40, 'CCC', '拒绝授信', 'red'),
]

# ─────────────────────────────────────────────
# 行业权重配置
# ─────────────────────────────────────────────

INDUSTRY_WEIGHTS = {
    '制造业': {
        'solvency':      0.30,
        'profitability': 0.25,
        'cashflow':      0.20,
        'operations':    0.15,
        'tax_compliance': 0.05,
        'fraud_alert':   0.05,
    },
    '零售/批发': {
        'solvency':      0.25,
        'profitability': 0.30,
        'cashflow':      0.25,
        'operations':    0.15,
        'tax_compliance': 0.05,
        'fraud_alert':   0.00,
    },
    '担保/金融服务': {
        'solvency':      0.35,
        'profitability': 0.20,
        'cashflow':      0.15,
        'operations':    0.10,
        'tax_compliance': 0.15,
        'fraud_alert':   0.05,
    },
    '建筑/地产': {
        'solvency':      0.30,
        'profitability': 0.20,
        'cashflow':      0.25,
        'operations':    0.10,
        'tax_compliance': 0.10,
        'fraud_alert':   0.05,
    },
    '农业/食品': {
        'solvency':      0.28,
        'profitability': 0.22,
        'cashflow':      0.22,
        'operations':    0.13,
        'tax_compliance': 0.10,
        'fraud_alert':   0.05,
    },
    '通用': {
        'solvency':      0.30,
        'profitability': 0.25,
        'cashflow':      0.20,
        'operations':    0.12,
        'tax_compliance': 0.08,
        'fraud_alert':   0.05,
    },
}

# ─────────────────────────────────────────────
# report_generator.py 常量
# ─────────────────────────────────────────────

# 金额单位
YI = 1e8
"""亿"""

WAN = 1e4
"""万"""

# 评分颜色阈值
SCORE_GOOD = 75
SCORE_MEDIUM = 60
SCORE_BAD = 40

# 评分颜色
SCORE_COLORS = {
    'good': '#1D9E75',
    'medium': '#EF9F27',
    'bad': '#D85A30',
    'very_bad': '#A32D2D',
}

# M-Score 因子阈值
FACTOR_UPPER = 1.1
FACTOR_LOWER = 0.9

# Q1 年化因子
Q1_ANNUALIZATION_FACTOR = 4
