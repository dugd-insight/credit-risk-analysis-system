# -*- coding: utf-8 -*-
"""
六维风险分析引擎 v2.0
- 行业差异化评分权重
- 跨期趋势指标（当有多期数据时自动激活）
- Beneish M-Score 财务造假预警
"""

from typing import Dict, List, Optional
import math


# ─────────────────────────────────────────────
# 通用平滑评分工具（sigmoid 映射到 0-100）
# 避免硬阈值分段导致的边界突变问题
# ─────────────────────────────────────────────

def _sigmoid_score(v: float, center: float, steepness: float = 8.0,
                   direction: str = 'higher_is_better') -> float:
    """
    sigmoid 连续映射：v → [0, 100]
    center    : 50 分对应的指标值（拐点）
    steepness : 曲线陡峭程度，越大越接近阶梯函数（建议 5-15）
    direction : 'higher_is_better' | 'lower_is_better'
    """
    if v is None:
        return 50.0
    if direction == 'lower_is_better':
        v = 2 * center - v   # 对称翻转
    try:
        score = 100.0 / (1.0 + math.exp(-steepness * (v - center) / (abs(center) + 1e-9)))
        return round(min(100.0, max(0.0, score)), 1)
    except Exception:
        return 50.0
from knowledge_base import get_triggered_rules, KNOWLEDGE_BASE


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

CREDIT_GRADES = [
    (90, 100, 'AAA', '建议足额授信', 'green'),
    (80,  90, 'AA',  '建议正常授信', 'green'),
    (70,  80, 'A',   '审慎授信', 'yellow'),
    (60,  70, 'BBB', '附条件授信', 'yellow'),
    (50,  60, 'BB',  '压缩授信额度', 'orange'),
    (40,  50, 'B',   '建议拒绝或要求强担保', 'red'),
    (0,   40, 'CCC', '拒绝授信', 'red'),
]


def get_credit_grade(score: float):
    for low, high, grade, suggestion, color in CREDIT_GRADES:
        if low <= score <= high:
            return grade, suggestion, color
    return 'CCC', '拒绝授信', 'red'


# ─────────────────────────────────────────────
# 数据完整性校验
# ─────────────────────────────────────────────

def _validate_financial_data(f: Dict) -> Dict:
    """
    校验财务数据逻辑合理性
    返回 {'warnings': [...], 'errors': [...]}
    """
    warnings = []
    errors = []

    ta = f.get('total_assets') or 0
    tl = f.get('total_liabilities') or 0
    te = f.get('total_equity') or 0

    # 1. 会计恒等式：资产 = 负债 + 权益（允许 5% 误差）
    if ta > 0 and tl > 0 and te > 0:
        diff_rate = abs(ta - tl - te) / ta
        if diff_rate > 0.05:
            warnings.append(
                f'会计恒等式不平衡：资产={ta/1e4:.1f}万，'
                f'负债+权益={(tl+te)/1e4:.1f}万，'
                f'差异率={diff_rate:.1%}（可能存在数据提取误差）'
            )

    # 2. 负债率合理性
    if ta > 0 and tl > ta * 1.2:
        errors.append(f'负债({tl/1e4:.1f}万)超过总资产({ta/1e4:.1f}万)120%，数据可能有误')

    # 3. 净利润 vs 利润总额一致性
    pbt = f.get('profit_before_tax') or 0
    np  = f.get('net_profit') or 0
    tax_f = f.get('income_tax') or 0
    if pbt != 0 and np != 0:
        implied_tax = pbt - np
        if tax_f > 0 and abs(implied_tax - tax_f) / (abs(pbt) + 1) > 0.3:
            warnings.append(
                f'所得税金额异常：利润总额-净利润={implied_tax/1e4:.1f}万，'
                f'财报所得税={tax_f/1e4:.1f}万，差异较大'
            )

    # 4. 流动资产不能超过总资产
    ca = f.get('current_assets') or 0
    if ca > 0 and ta > 0 and ca > ta * 1.05:
        warnings.append(f'流动资产({ca/1e4:.1f}万)超过总资产({ta/1e4:.1f}万)，数据可能有误')

    # 5. 营业收入与成本关系（成本不应超过收入3倍，否则异常）
    rev  = f.get('revenue') or 0
    cogs = f.get('cost_of_sales') or 0
    if rev > 0 and cogs > rev * 3:
        warnings.append(f'营业成本({cogs/1e4:.1f}万)远超收入({rev/1e4:.1f}万)，请核实')

    return {'warnings': warnings, 'errors': errors}

# ─────────────────────────────────────────────
# 基础工具
# ─────────────────────────────────────────────

def safe_div(a, b, default=None):
    try:
        if b and abs(b) > 1e-9:
            return a / b
        return default
    except Exception:
        return default


def _pct_change(new_val, old_val):
    """计算变化率：(new - old) / |old|"""
    if old_val is None or new_val is None:
        return None
    if abs(old_val) < 1e-6:
        return None
    return (new_val - old_val) / abs(old_val)


# ─────────────────────────────────────────────
# 主指标计算
# ─────────────────────────────────────────────

def calculate_metrics(fin: Dict[str, float], tax: Dict[str, float],
                       fin_prev: Optional[Dict[str, float]] = None) -> Dict:
    """
    计算所有分析指标
    fin: 最新期财务数据
    tax: 税务数据
    fin_prev: 上一期财务数据（用于趋势分析，可选）
    返回：{指标名: {value, score, triggered_rules, ...}}
    """
    f = fin
    fp = fin_prev or {}
    metrics = {}

    # ────────── 数据完整性校验（先于所有计算）──────────
    validation = _validate_financial_data(f)
    if validation['warnings']:
        metrics['__data_warnings__'] = {
            'label': '数据校验警告',
            'value': len(validation['warnings']),
            'warnings': validation['warnings'],
            'score': max(0, 100 - len(validation['warnings']) * 20),
            'triggered_rules': [],
        }

    # ────────── 偿债能力 ──────────
    current_assets    = f.get('current_assets', 0) or 0
    current_liab      = f.get('current_liabilities', 0) or 0
    cash              = f.get('cash', 0) or 0
    inventory         = f.get('inventory', 0) or 0
    total_assets      = f.get('total_assets', 0) or 0
    total_liabilities = f.get('total_liabilities', 0) or 0
    total_equity      = f.get('total_equity', 0) or 0
    interest_expense  = f.get('interest_expense') or f.get('finance_cost') or f.get('business_tax', 0) or 0
    net_profit        = f.get('net_profit', 0) or 0
    profit_before_tax = f.get('profit_before_tax', 0) or 0
    operating_profit  = f.get('operating_profit', 0) or 0

    # 流动比率
    cr = safe_div(current_assets, current_liab)
    metrics['current_ratio'] = {
        'label': '流动比率',
        'value': cr,
        'unit': '倍',
        'benchmark': '≥ 1.5（安全）',
        'score': _score_current_ratio(cr),
        'triggered_rules': get_triggered_rules('current_ratio', cr) if cr is not None else [],
    }

    # 速动比率
    qr = safe_div(current_assets - inventory, current_liab)
    metrics['quick_ratio'] = {
        'label': '速动比率',
        'value': qr,
        'unit': '倍',
        'benchmark': '≥ 1.0（安全）',
        'score': _score_quick_ratio(qr),
        'triggered_rules': get_triggered_rules('quick_ratio', qr) if qr is not None else [],
    }

    # 资产负债率
    dr = safe_div(total_liabilities, total_assets)
    metrics['debt_ratio'] = {
        'label': '资产负债率',
        'value': dr,
        'unit': '%',
        'benchmark': '< 70%（警戒）',
        'score': _score_debt_ratio(dr),
        'triggered_rules': get_triggered_rules('debt_ratio', dr) if dr is not None else [],
    }

    # 利息保障倍数（担保公司无利息负债时用营业利润/营业税金代替）
    ebit = profit_before_tax + interest_expense
    icr = safe_div(ebit, interest_expense) if interest_expense > 0 else None
    # 担保公司：若无利息，用营业利润是否充裕来评分
    if icr is None and operating_profit > 0:
        icr = operating_profit / max(total_liabilities * 0.05, 1)  # 假设5%融资成本
    metrics['interest_coverage'] = {
        'label': '利息保障倍数',
        'value': icr,
        'unit': '倍',
        'benchmark': '≥ 3（优良）',
        'score': _score_icr(icr),
        'triggered_rules': get_triggered_rules('interest_coverage', icr) if icr is not None else [],
    }

    # ────────── 盈利能力 ──────────
    revenue      = f.get('revenue', 0) or 0
    cost_of_sales = f.get('cost_of_sales', 0) or 0
    income_tax   = f.get('income_tax', 0) or 0

    # 毛利率
    gross_profit = revenue - cost_of_sales
    gpm = safe_div(gross_profit, revenue)
    metrics['gross_profit_margin'] = {
        'label': '毛利率（担保费净收益率）',
        'value': gpm,
        'unit': '%',
        'benchmark': '担保行业：≥ 20%',
        'score': _score_margin(gpm, 0.15, 0.35),
        'triggered_rules': [],
    }

    # 净利率
    npm = safe_div(net_profit, revenue)
    metrics['net_profit_margin'] = {
        'label': '净利率',
        'value': npm,
        'unit': '%',
        'benchmark': '> 5%（基准）',
        'score': _score_margin(npm, 0.03, 0.15),
        'triggered_rules': [],
    }

    # ROE（净资产收益率）
    # 如果是Q1季度数据（从 periods 无法直接获知，通过 fin_prev 判断），折年化
    # 简单处理：如果上期为全年，当前期净利润可能是Q1，折年化评分
    roe_raw = safe_div(net_profit, total_equity)
    # 检查是否需要折年化（当利润远小于上一期时，认为是季度数据）
    roe_annualized = None
    if roe_raw is not None and fp:
        prev_np = fp.get('net_profit', 0) or 0
        prev_eq = fp.get('total_equity', 0) or 0
        if prev_np > 0 and net_profit > 0 and net_profit < prev_np * 0.5:
            # 当前期净利润显著小于上期，推断为季度数据，折年化（×4）
            roe_annualized = safe_div(net_profit * 4, total_equity)
    roe = roe_annualized if roe_annualized is not None else roe_raw
    roe_label = '净资产收益率(ROE，折年)' if roe_annualized is not None else '净资产收益率(ROE)'
    metrics['roe'] = {
        'label': roe_label,
        'value': roe,
        'unit': '%',
        'benchmark': '> 10%（优良）',
        'score': _score_margin(roe, 0.05, 0.15),
        'triggered_rules': get_triggered_rules('roe', roe) if roe is not None else [],
    }

    # ROA（总资产收益率）
    roa = safe_div(net_profit, total_assets)
    metrics['roa'] = {
        'label': '总资产收益率(ROA)',
        'value': roa,
        'unit': '%',
        'benchmark': '> 3%（基准）',
        'score': _score_margin(roa, 0.02, 0.08),
        'triggered_rules': [],
    }

    # 实际所得税率
    etr = safe_div(income_tax, profit_before_tax)
    metrics['effective_tax_rate'] = {
        'label': '实际所得税率',
        'value': etr,
        'unit': '%',
        'benchmark': '15%~25%（正常区间）',
        'score': _score_tax_rate(etr),
        'triggered_rules': get_triggered_rules('effective_tax_rate', etr) if etr is not None else [],
    }

    # ────────── 现金流 ──────────
    operating_cashflow = f.get('operating_cashflow') or 0
    cash_from_sales    = f.get('cash_from_sales', 0) or 0

    # 若无现金流量表但有利润数据，用间接法估算经营现金流
    # 担保公司：经营现金流 ≈ 净利润 + 折旧摊销 - 应收款增加
    if operating_cashflow == 0 and net_profit:
        depreciation = f.get('depreciation', 0) or 0
        amortization = f.get('amortization', 0) or (f.get('long_term_prepaid', 0) or 0) * 0.1
        ar_prev = fp.get('accounts_receivable', 0) or 0 if fp else 0
        ar_curr = f.get('accounts_receivable', 0) or 0
        ar_change = ar_curr - ar_prev
        estimated_cf = net_profit + depreciation + amortization - ar_change
        operating_cashflow = estimated_cf
        cf_is_estimated = True
    else:
        cf_is_estimated = False

    cf_label = '经营活动净现金流（估算）' if cf_is_estimated else '经营活动净现金流'

    metrics['operating_cashflow'] = {
        'label': cf_label,
        'value': operating_cashflow,
        'unit': '元',
        'benchmark': '> 0（正向）',
        'score': _score_cashflow(operating_cashflow),
        'triggered_rules': get_triggered_rules('operating_cashflow', operating_cashflow),
    }

    # 现金比率
    cash_ratio = safe_div(cash, current_liab)
    metrics['cash_ratio'] = {
        'label': '现金比率',
        'value': cash_ratio,
        'unit': '倍',
        'benchmark': '≥ 0.2（安全）',
        'score': _score_cash_ratio(cash_ratio),
        'triggered_rules': [],
    }

    # 利润现金含金量
    cpr = safe_div(operating_cashflow, net_profit) if net_profit else None
    metrics['cash_profit_ratio'] = {
        'label': '利润现金含金量',
        'value': cpr,
        'unit': '倍',
        'benchmark': '≥ 1.0（优良）',
        'score': _score_margin(cpr, 0.5, 1.0) if cpr is not None else 50,
        'triggered_rules': get_triggered_rules('cash_profit_ratio', cpr) if cpr is not None else [],
    }

    # 销售收现比
    csr = safe_div(cash_from_sales, revenue) if revenue else None
    metrics['cash_sales_ratio'] = {
        'label': '销售收现比',
        'value': csr,
        'unit': '倍',
        'benchmark': '≥ 0.9（优良）',
        'score': _score_margin(csr, 0.7, 1.0) if csr is not None else 50,
        'triggered_rules': [],
    }

    # ────────── 营运能力 ──────────
    accounts_receivable = f.get('accounts_receivable', 0) or 0
    deposit_out = f.get('deposit_out', 0) or 0

    # 应收账款周转率（担保公司：应收款含存出保证金）
    effective_ar = accounts_receivable + deposit_out  # 担保公司：应收类资产
    ar_turnover = safe_div(revenue, effective_ar) if effective_ar > 0 else None
    metrics['ar_turnover'] = {
        'label': '应收/保证金周转率',
        'value': ar_turnover,
        'unit': '次/年',
        'benchmark': '越高越好',
        'score': _score_turnover(ar_turnover, 1, 3),  # 担保行业低基准
        'triggered_rules': [],
    }

    # 应收账款周转天数
    ar_days = safe_div(365, ar_turnover) if ar_turnover else None
    metrics['ar_days'] = {
        'label': '应收/保证金周转天数',
        'value': ar_days,
        'unit': '天',
        'benchmark': '< 180天（担保行业）',
        'score': _score_ar_days_guarantee(ar_days),
        'triggered_rules': [],
    }

    # 总资产周转率
    asset_turnover = safe_div(revenue, total_assets)
    metrics['asset_turnover'] = {
        'label': '总资产周转率',
        'value': asset_turnover,
        'unit': '次/年',
        'benchmark': '> 0.3（担保行业）',
        'score': _score_turnover(asset_turnover, 0.1, 0.5),
        'triggered_rules': [],
    }

    # 担保专项：净资本充足率（实收资本/总资产）
    capital_adequacy = safe_div(f.get('paid_in_capital', 0) or 0, total_assets)
    metrics['capital_adequacy'] = {
        'label': '净资本充足率',
        'value': capital_adequacy,
        'unit': '%',
        'benchmark': '担保公司：≥ 40%',
        'score': _score_margin(capital_adequacy, 0.3, 0.6),
        'triggered_rules': [],
    }

    # ────────── 税务合规 ──────────
    vat_sales = tax.get('vat_taxable_sales', 0)
    if vat_sales and revenue and vat_sales > 0:
        vat_gap = abs(vat_sales - revenue) / revenue
        metrics['vat_revenue_gap'] = {
            'label': '增值税收入-财报收入差异率',
            'value': vat_gap,
            'unit': '%',
            'benchmark': '< 15%（正常）',
            'score': max(0, 100 - vat_gap * 300),
            'triggered_rules': get_triggered_rules('vat_revenue_gap', vat_gap),
        }
    else:
        # 无税务申报数据时，税务合规维度给中性分（60分，不扣分不加分）
        metrics['vat_revenue_gap'] = {
            'label': '增值税申报核验',
            'value': None,
            'unit': '',
            'benchmark': '无增值税申报数据',
            'score': 60,
            'triggered_rules': [],
            'note': '未提供增值税申报表，无法核验收入一致性',
        }

    # ────────── 跨期趋势分析（当有上期数据时） ──────────
    if fp:
        trend_metrics = _calculate_trend_metrics(f, fp)
        metrics.update(trend_metrics)

    # ────────── Beneish M-Score（支持双期，精度更高）──────────
    m_score = _calculate_m_score(f, fp if fp else None)
    if m_score is not None:
        metrics['m_score'] = {
            'label': 'Beneish M-Score（造假预警）',
            'value': m_score,
            'unit': '',
            'benchmark': '< -1.78（安全）',
            'score': 100 if m_score < -2.22 else (50 if m_score < -1.78 else 0),
            'triggered_rules': get_triggered_rules('m_score', m_score),
        }

    return metrics


# ─────────────────────────────────────────────
# 跨期趋势指标
# ─────────────────────────────────────────────

def _calculate_trend_metrics(f_new: Dict, f_old: Dict) -> Dict:
    """
    基于两期数据计算趋势指标
    2025-12 为旧期（全年），2026-03 为新期（季度）
    注意：季度收入 × 4 才能与全年对比（需折年化处理）
    """
    metrics = {}

    def pct(key, annualize_new=False, annualize_factor=4):
        """计算增长率，annualize_new：新期数值是否需要折年化"""
        new_v = f_new.get(key)
        old_v = f_old.get(key)
        if new_v is None or old_v is None or abs(old_v) < 1:
            return None
        if annualize_new:
            new_v = new_v * annualize_factor
        return (new_v - old_v) / abs(old_v)

    # 资产规模变化
    asset_growth = pct('total_assets')
    if asset_growth is not None:
        metrics['asset_growth'] = {
            'label': '总资产增长率（期末对比）',
            'value': asset_growth,
            'unit': '%',
            'benchmark': '> 0（扩张）',
            'score': _score_growth(asset_growth, 0, 0.3),
            'triggered_rules': [],
            'trend_type': True,
        }

    # 权益规模变化
    equity_growth = pct('total_equity')
    if equity_growth is not None:
        metrics['equity_growth'] = {
            'label': '所有者权益增长率',
            'value': equity_growth,
            'unit': '%',
            'benchmark': '> 0（净资产增厚）',
            'score': _score_growth(equity_growth, 0, 0.2),
            'triggered_rules': [],
            'trend_type': True,
        }

    # 收入趋势（季度年化 vs 全年）
    rev_new = f_new.get('revenue')
    rev_old = f_old.get('revenue')
    if rev_new is not None and rev_old is not None and rev_old > 0:
        # 2026Q1收入 * 4 与2025全年收入对比（隐含年增长率）
        rev_annualized = rev_new * 4
        rev_growth_yoy = (rev_annualized - rev_old) / rev_old
        metrics['revenue_growth_yoy'] = {
            'label': '收入年化增速（Q1折年 vs 全年）',
            'value': rev_growth_yoy,
            'unit': '%',
            'benchmark': '> 10%（良好）',
            'score': _score_growth(rev_growth_yoy, 0, 0.2),
            'triggered_rules': [],
            'trend_type': True,
        }

    # 利润变化
    profit_growth = None
    np_new = f_new.get('net_profit')
    np_old = f_old.get('net_profit')
    if np_new is not None and np_old is not None and np_old > 0:
        profit_annualized = np_new * 4
        profit_growth = (profit_annualized - np_old) / np_old
        metrics['profit_growth_yoy'] = {
            'label': '利润年化增速（Q1折年 vs 全年）',
            'value': profit_growth,
            'unit': '%',
            'benchmark': '> 0（持续盈利）',
            'score': _score_growth(profit_growth, -0.1, 0.2),
            'triggered_rules': [],
            'trend_type': True,
        }

    # 负债率变化趋势
    dr_new = f_new.get('total_liabilities', 0) / max(f_new.get('total_assets', 1), 1)
    dr_old = f_old.get('total_liabilities', 0) / max(f_old.get('total_assets', 1), 1)
    dr_change = dr_new - dr_old
    metrics['debt_ratio_change'] = {
        'label': '资产负债率变动（最新-上期）',
        'value': dr_change,
        'unit': '%',
        'benchmark': '< 0（负债率下降）',
        'score': max(0, 70 - abs(dr_change) * 500) if dr_change > 0 else min(100, 80 + abs(dr_change) * 500),
        'triggered_rules': [],
        'trend_type': True,
    }

    # 应收账款变化（担保公司：关注存出保证金异常变化）
    deposit_change = pct('deposit_out')
    if deposit_change is not None:
        metrics['deposit_out_change'] = {
            'label': '存出保证金变动率',
            'value': deposit_change,
            'unit': '%',
            'benchmark': '< 30%（稳定）',
            'score': max(0, 80 - abs(deposit_change) * 100) if abs(deposit_change) > 0.3 else 85,
            'triggered_rules': [],
            'trend_type': True,
        }

    # 跨期异常检测（FRAUD-002触发条件）
    cross_period_anomaly = _detect_cross_period_anomaly(f_new, f_old)
    if cross_period_anomaly is not None:
        metrics['cross_period_anomaly'] = {
            'label': '跨期数据一致性异常度',
            'value': cross_period_anomaly,
            'unit': '',
            'benchmark': '< 0.2（正常）',
            'score': max(0, 100 - cross_period_anomaly * 300),
            'triggered_rules': get_triggered_rules('cross_period_anomaly', cross_period_anomaly),
            'trend_type': True,
        }

    return metrics


def _detect_cross_period_anomaly(f_new: Dict, f_old: Dict) -> Optional[float]:
    """
    跨期数据倒挂异常检测
    检查：期末流动资产 < 年初流动资产 × 0.5 等异常
    返回异常度 0~1（0=正常，1=严重异常）
    """
    anomaly_scores = []

    # 检查总资产是否出现大幅下降（正常扩张期不应下降超20%）
    ta_new = f_new.get('total_assets', 0) or 0
    ta_old = f_old.get('total_assets', 0) or 0
    if ta_old > 0 and ta_new < ta_old * 0.7:
        anomaly_scores.append(0.8)
    elif ta_old > 0 and ta_new > 0:
        anomaly_scores.append(0.0)

    # 利润与收入增长方向是否一致（Q1折年）
    rev_new = (f_new.get('revenue') or 0) * 4
    rev_old = f_old.get('revenue') or 0
    np_new = (f_new.get('net_profit') or 0) * 4
    np_old = f_old.get('net_profit') or 0
    if rev_old > 0 and np_old > 0:
        rev_dir = 1 if rev_new > rev_old else -1
        np_dir = 1 if np_new > np_old else -1
        if rev_dir != np_dir:
            anomaly_scores.append(0.4)  # 收入利润方向不一致
        else:
            anomaly_scores.append(0.0)

    return round(sum(anomaly_scores) / max(len(anomaly_scores), 1), 3) if anomaly_scores else None


# ─────────────────────────────────────────────
# Beneish M-Score（完整 8 因子实现）
# Beneish (1999): M = -4.84 + 0.920*DSRI + 0.528*GMI + 0.404*AQI
#                      + 0.892*SGI + 0.115*DEPI - 0.172*SGAI
#                      + 4.679*TATA - 0.327*LVGI
# 阈值：> -1.78 表示财务造假风险高，> -2.22 表示中等风险
# ─────────────────────────────────────────────

def _calculate_m_score(f: Dict, f_prev: Optional[Dict] = None) -> Optional[float]:
    """
    完整 Beneish 8 因子 M-Score
    f      : 当期财务数据
    f_prev : 上期财务数据（提供时因子更准确）
    """
    try:
        # 当期核心数值
        rev   = f.get('revenue') or 0
        ar    = f.get('accounts_receivable') or 0
        cost  = f.get('cost_of_sales') or 0
        ta    = f.get('total_assets') or 1
        fa    = f.get('fixed_assets') or f.get('fixed_assets_gross') or 0
        pp    = f.get('long_term_prepaid') or 0          # 其他资产（AQI代理）
        depr  = f.get('depreciation') or 0               # 折旧
        sga   = (f.get('selling_expense') or 0) + (f.get('admin_expense') or 0)
        tl    = f.get('total_liabilities') or 0
        te    = f.get('total_equity') or (ta - tl)
        ocf   = f.get('operating_cashflow') or 0
        np    = f.get('net_profit') or 0

        if rev <= 0 or ta <= 0:
            return None

        gp    = rev - cost
        gross_margin = gp / rev

        # ── 单期可计算的因子（无上期数据时设为中性值）──
        # TATA: 应计利润比率（总资产应计项目）
        tata = (np - ocf) / ta

        if f_prev:
            rev0  = f_prev.get('revenue') or 1
            ar0   = f_prev.get('accounts_receivable') or 0
            cost0 = f_prev.get('cost_of_sales') or 0
            ta0   = f_prev.get('total_assets') or 1
            fa0   = f_prev.get('fixed_assets') or f_prev.get('fixed_assets_gross') or 0
            pp0   = f_prev.get('long_term_prepaid') or 0
            depr0 = f_prev.get('depreciation') or 0
            sga0  = (f_prev.get('selling_expense') or 0) + (f_prev.get('admin_expense') or 0)
            tl0   = f_prev.get('total_liabilities') or 0
            te0   = f_prev.get('total_equity') or (ta0 - tl0)
            gp0   = rev0 - cost0
            gm0   = gp0 / rev0 if rev0 else 0

            # DSRI: 应收账款增速 / 收入增速（>1 表示应收增长快于收入，收入质量下降）
            dsri = (ar / rev) / (ar0 / rev0) if ar0 > 0 else (ar / rev + 1)

            # GMI: 毛利率指数（>1 表示毛利率下降）
            gmi = gm0 / gross_margin if gross_margin > 0 else 1.0

            # AQI: 资产质量指数（非流动非固定资产占比变化）
            aqi_curr = 1 - (fa + (f.get('current_assets') or 0)) / ta
            aqi_prev = 1 - (fa0 + (f_prev.get('current_assets') or 0)) / ta0
            aqi = aqi_curr / aqi_prev if aqi_prev > 0 else 1.0

            # SGI: 营收增长指数（>1 表示高增长，可能有激励造假）
            sgi = rev / rev0 if rev0 > 0 else 1.0

            # DEPI: 折旧指数（>1 表示折旧减少，可能低估资产损耗）
            dep_rate0 = depr0 / (fa0 + depr0) if (fa0 + depr0) > 0 else 0
            dep_rate  = depr / (fa + depr) if (fa + depr) > 0 else dep_rate0
            depi = dep_rate0 / dep_rate if dep_rate > 0 else 1.0

            # SGAI: 销售管理费用指数（>1 表示费用增速快于收入）
            sgai = (sga / rev) / (sga0 / rev0) if (sga0 > 0 and rev0 > 0) else 1.0

            # LVGI: 杠杆指数（>1 表示负债增加）
            lev_curr = tl / (tl + te) if (tl + te) > 0 else 0
            lev_prev = tl0 / (tl0 + te0) if (tl0 + te0) > 0 else 0
            lvgi = lev_curr / lev_prev if lev_prev > 0 else 1.0

        else:
            # 无上期数据：使用保守中性值，仅 DSRI / TATA 可单期估算
            dsri = (ar / rev) / 0.1 if rev > 0 else 1.0   # 假设历史AR/Rev = 10%
            dsri = min(dsri, 3.0)                            # 防止极端值
            gmi  = 1.0
            aqi  = 1.0
            sgi  = 1.0
            depi = 1.0
            sgai = 1.0
            lvgi = 1.0

        m = (-4.84
             + 0.920 * dsri
             + 0.528 * gmi
             + 0.404 * aqi
             + 0.892 * sgi
             + 0.115 * depi
             - 0.172 * sgai
             + 4.679 * tata
             - 0.327 * lvgi)

        return round(m, 3)
    except Exception:
        return None


# ─────────────────────────────────────────────
# 评分函数（0-100，sigmoid 平滑，无硬边界突变）
# ─────────────────────────────────────────────

def _score_current_ratio(v):
    """流动比率：center=2.0（担保公司通常极高，上限软化）"""
    if v is None: return 50
    # 担保公司流动比率 5~30 属正常，不应过度加分
    capped = min(v, 15.0)
    return _sigmoid_score(capped, center=2.0, steepness=6.0)


def _score_quick_ratio(v):
    """速动比率：center=1.2"""
    if v is None: return 50
    capped = min(v, 12.0)
    return _sigmoid_score(capped, center=1.2, steepness=7.0)


def _score_debt_ratio(v):
    """资产负债率：越低越好，center=0.55（55%为拐点）"""
    if v is None: return 50
    return _sigmoid_score(v, center=0.55, steepness=8.0, direction='lower_is_better')


def _score_icr(v):
    """利息保障倍数：center=3.0"""
    if v is None: return 60   # 担保公司无有息负债时给中等分
    capped = min(v, 30.0)
    return _sigmoid_score(capped, center=3.0, steepness=5.0)


def _score_margin(v, low, high):
    """通用利润率/比率评分，center 取 (low+high)/2"""
    if v is None: return 50
    center = (low + high) / 2.0
    return _sigmoid_score(v, center=center, steepness=8.0)


def _score_cashflow(v):
    """经营净现金流：正为好，以总资产1%为拐点"""
    if v is None: return 50
    # 用万元归一化，避免绝对金额影响斜率
    v_norm = v / 1e4
    return _sigmoid_score(v_norm, center=0.0, steepness=0.3)


def _score_cash_ratio(v):
    """现金比率：center=0.4（担保公司可略高）"""
    if v is None: return 50
    capped = min(v, 5.0)
    return _sigmoid_score(capped, center=0.4, steepness=6.0)


def _score_tax_rate(v):
    """有效税率：15%-25% 最优，过低过高均扣分"""
    if v is None: return 60
    # 最优区间中心 = 0.20
    optimal = 0.20
    deviation = abs(v - optimal)
    return max(0.0, round(100.0 - deviation * 300, 1))


def _score_turnover(v, low, high):
    """周转率：center = (low + high) / 2"""
    if v is None: return 50
    center = (low + high) / 2.0
    return _sigmoid_score(v, center=center, steepness=5.0)


def _score_ar_days_guarantee(v):
    """担保保证金周转天数：越短越好，center=365天"""
    if v is None: return 60
    return _sigmoid_score(v, center=365.0, steepness=2.0, direction='lower_is_better')


def _score_growth(v, low, high):
    """增长率评分：center = (low + high) / 2"""
    if v is None: return 50
    center = (low + high) / 2.0 if (low + high) != 0 else 0.1
    return _sigmoid_score(v, center=center, steepness=10.0)


# ─────────────────────────────────────────────
# 综合评分引擎
# ─────────────────────────────────────────────

DIMENSION_METRIC_MAP = {
    'solvency':       ['current_ratio', 'quick_ratio', 'debt_ratio', 'interest_coverage'],
    'profitability':  ['gross_profit_margin', 'net_profit_margin', 'roe', 'roa', 'effective_tax_rate'],
    'cashflow':       ['operating_cashflow', 'cash_ratio', 'cash_profit_ratio', 'cash_sales_ratio'],
    'operations':     ['ar_turnover', 'ar_days', 'asset_turnover', 'capital_adequacy'],
    'tax_compliance': ['vat_revenue_gap', 'effective_tax_rate'],
    'fraud_alert':    ['m_score', 'cross_period_anomaly'],
}


def compute_dimension_score(metrics: Dict, dimension: str) -> float:
    keys = DIMENSION_METRIC_MAP.get(dimension, [])
    scores = [metrics[k]['score'] for k in keys if k in metrics and metrics[k].get('score') is not None]
    if not scores:
        return 60.0
    return round(sum(scores) / len(scores), 1)


def compute_total_score(metrics: Dict, industry: str = '通用') -> Dict:
    weights = INDUSTRY_WEIGHTS.get(industry, INDUSTRY_WEIGHTS['通用'])
    dim_scores = {}
    for dim in weights:
        dim_scores[dim] = compute_dimension_score(metrics, dim)

    # 造假预警一票否决
    m_score_val = metrics.get('m_score', {}).get('value')
    veto = m_score_val is not None and m_score_val > -1.78

    if veto:
        total = 0.0
        grade, suggestion, color = 'CCC', '一票否决：财务造假风险极高，拒绝授信', 'red'
    else:
        total = round(sum(dim_scores[d] * weights[d] for d in weights), 1)
        grade, suggestion, color = get_credit_grade(total)

    return {
        'total_score':      total,
        'grade':            grade,
        'suggestion':       suggestion,
        'color':            color,
        'veto':             veto,
        'dimension_scores': dim_scores,
        'weights':          weights,
        'industry':         industry,
    }
