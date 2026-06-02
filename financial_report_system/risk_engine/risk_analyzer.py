# -*- coding: utf-8 -*-
"""
六维风险分析引擎 v3.0
- 行业差异化评分权重
- 跨期趋势指标（当有多期数据时自动激活）
- Beneish M-Score 财务造假预警
- 模块化指标计算（拆分自原 calculate_metrics）
"""

from typing import Dict, List, Optional, Tuple
import math

from knowledge_base import get_triggered_rules, KNOWLEDGE_BASE
from constants import (
    EPSILON, ACCOUNTING_EQUATION_TOLERANCE, DEBT_RATIO_ERROR_THRESHOLD,
    TAX_DIFF_TOLERANCE, CURRENT_ASSETS_MAX_RATIO, COST_REVENUE_MAX_RATIO,
    ASSUMED_FINANCING_COST, GPM_LOW, GPM_HIGH, NPM_LOW, NPM_HIGH,
    ROE_LOW, ROE_HIGH, ROA_LOW, ROA_HIGH, GROWTH_NEUTRAL, GROWTH_GOOD,
    VAT_GAP_PENALTY_FACTOR, MSCORE_SAFE, MSCORE_DANGER,
    BENEISH_COEFFICIENTS, CURRENT_RATIO_CAP, CURRENT_RATIO_CENTER,
    CURRENT_RATIO_STEEPNESS, QUICK_RATIO_CAP, QUICK_RATIO_CENTER,
    QUICK_RATIO_STEEPNESS, DEBT_RATIO_CENTER, DEBT_RATIO_STEEPNESS,
    ICR_CAP, ICR_CENTER, ICR_STEEPNESS, CASH_RATIO_CAP, CASH_RATIO_CENTER,
    CASH_RATIO_STEEPNESS, TAX_RATE_OPTIMAL, TAX_RATE_PENALTY,
    TURNOVER_STEEPNESS, GROWTH_STEEPNESS, DEBT_RATIO_CHANGE_PENALTY,
    DEPOSIT_CHANGE_THRESHOLD, DEPOSIT_CHANGE_PENALTY,
    ASSET_DECLINE_THRESHOLD, ANOMALY_SCORE_INCONSISTENT,
    ASSUMED_AR_REVENUE_RATIO, DSRI_CAP, INDUSTRY_WEIGHTS, CREDIT_GRADES
)


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
        score = 100.0 / (1.0 + math.exp(-steepness * (v - center) / (abs(center) + EPSILON)))
        return round(min(100.0, max(0.0, score)), 1)
    except Exception:
        return 50.0


def get_credit_grade(score: float) -> Tuple[str, str, str]:
    """根据分数获取信用等级、建议和颜色"""
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

    # 1. 会计恒等式：资产 = 负债 + 权益
    if ta > 0 and tl > 0 and te > 0:
        diff_rate = abs(ta - tl - te) / ta
        if diff_rate > ACCOUNTING_EQUATION_TOLERANCE:
            warnings.append(
                f'会计恒等式不平衡：资产={ta/1e4:.1f}万，'
                f'负债+权益={(tl+te)/1e4:.1f}万，'
                f'差异率={diff_rate:.1%}（可能存在数据提取误差）'
            )

    # 2. 负债率合理性
    if ta > 0 and tl > ta * DEBT_RATIO_ERROR_THRESHOLD:
        errors.append(f'负债({tl/1e4:.1f}万)超过总资产({ta/1e4:.1f}万)120%，数据可能有误')

    # 3. 净利润 vs 利润总额一致性
    pbt = f.get('profit_before_tax') or 0
    np  = f.get('net_profit') or 0
    tax_f = f.get('income_tax') or 0
    if pbt != 0 and np != 0:
        implied_tax = pbt - np
        if tax_f > 0 and abs(implied_tax - tax_f) / (abs(pbt) + 1) > TAX_DIFF_TOLERANCE:
            warnings.append(
                f'所得税金额异常：利润总额-净利润={implied_tax/1e4:.1f}万，'
                f'财报所得税={tax_f/1e4:.1f}万，差异较大'
            )

    # 4. 流动资产不能超过总资产
    ca = f.get('current_assets') or 0
    if ca > 0 and ta > 0 and ca > ta * CURRENT_ASSETS_MAX_RATIO:
        warnings.append(f'流动资产({ca/1e4:.1f}万)超过总资产({ta/1e4:.1f}万)，数据可能有误')

    # 5. 营业收入与成本关系
    rev  = f.get('revenue') or 0
    cogs = f.get('cost_of_sales') or 0
    if rev > 0 and cogs > rev * COST_REVENUE_MAX_RATIO:
        warnings.append(f'营业成本({cogs/1e4:.1f}万)远超收入({rev/1e4:.1f}万)，请核实')

    return {'warnings': warnings, 'errors': errors}


# ─────────────────────────────────────────────
# 基础工具
# ─────────────────────────────────────────────

def safe_div(a: float, b: float, default: Optional[float] = None) -> Optional[float]:
    """安全除法，避免除零错误"""
    try:
        if b and abs(b) > EPSILON:
            return a / b
        return default
    except Exception:
        return default


# ─────────────────────────────────────────────
# 分维度指标计算（拆分自原 calculate_metrics）
# ─────────────────────────────────────────────

def _calculate_data_validation(f: Dict) -> Dict:
    """计算数据校验指标"""
    metrics = {}
    validation = _validate_financial_data(f)
    if validation['warnings']:
        metrics['__data_warnings__'] = {
            'label': '数据校验警告',
            'value': len(validation['warnings']),
            'warnings': validation['warnings'],
            'score': max(0, 100 - len(validation['warnings']) * 20),
            'triggered_rules': [],
        }
    return metrics


def _calculate_solvency_metrics(f: Dict) -> Dict:
    """计算偿债能力指标"""
    metrics = {}

    current_assets    = f.get('current_assets', 0) or 0
    current_liab      = f.get('current_liabilities', 0) or 0
    cash              = f.get('cash', 0) or 0
    inventory         = f.get('inventory', 0) or 0
    total_assets      = f.get('total_assets', 0) or 0
    total_liabilities = f.get('total_liabilities', 0) or 0
    interest_expense  = f.get('interest_expense') or f.get('finance_cost_interest') or f.get('finance_cost') or 0
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

    # 利息保障倍数
    ebit = profit_before_tax + interest_expense
    icr = safe_div(ebit, interest_expense) if interest_expense > 0 else None
    if icr is None and operating_profit > 0:
        icr = operating_profit / max(total_liabilities * ASSUMED_FINANCING_COST, 1)
    metrics['interest_coverage'] = {
        'label': '利息保障倍数',
        'value': icr,
        'unit': '倍',
        'benchmark': '≥ 3（优良）',
        'score': _score_icr(icr),
        'triggered_rules': get_triggered_rules('interest_coverage', icr) if icr is not None else [],
    }

    return metrics


def _calculate_profitability_metrics(f: Dict, fp: Dict) -> Dict:
    """计算盈利能力指标"""
    metrics = {}

    revenue       = f.get('revenue', 0) or 0
    cost_of_sales = f.get('cost_of_sales', 0) or 0
    net_profit    = f.get('net_profit', 0) or 0
    total_equity  = f.get('total_equity', 0) or 0
    total_assets  = f.get('total_assets', 0) or 0
    income_tax    = f.get('income_tax', 0) or 0
    profit_before_tax = f.get('profit_before_tax', 0) or 0

    # 毛利率
    gross_profit = revenue - cost_of_sales
    gpm = safe_div(gross_profit, revenue)
    metrics['gross_profit_margin'] = {
        'label': '毛利率（担保费净收益率）',
        'value': gpm,
        'unit': '%',
        'benchmark': '担保行业：≥ 20%',
        'score': _score_margin(gpm, GPM_LOW, GPM_HIGH),
        'triggered_rules': [],
    }

    # 净利率
    npm = safe_div(net_profit, revenue)
    metrics['net_profit_margin'] = {
        'label': '净利率',
        'value': npm,
        'unit': '%',
        'benchmark': '> 5%（基准）',
        'score': _score_margin(npm, NPM_LOW, NPM_HIGH),
        'triggered_rules': [],
    }

    # ROE（净资产收益率）
    roe_raw = safe_div(net_profit, total_equity)
    roe = roe_raw
    roe_annualized = None
    ann_factor = f.get('_annualization_factor', 1.0)
    if ann_factor <= 1.0 and roe_raw is not None and fp:
        prev_np = fp.get('net_profit', 0) or 0
        prev_eq = fp.get('total_equity', 0) or 0
        if prev_np > 0 and net_profit > 0 and net_profit < prev_np * 0.5:
            roe_annualized = safe_div(net_profit * 4, total_equity)
            roe = roe_annualized
    roe_label = '净资产收益率(ROE，折年)' if roe_annualized is not None else '净资产收益率(ROE)'
    metrics['roe'] = {
        'label': roe_label,
        'value': roe,
        'unit': '%',
        'benchmark': '> 10%（优良）',
        'score': _score_margin(roe, ROE_LOW, ROE_HIGH),
        'triggered_rules': get_triggered_rules('roe', roe) if roe is not None else [],
    }

    # ROA（总资产收益率）
    roa = safe_div(net_profit, total_assets)
    metrics['roa'] = {
        'label': '总资产收益率(ROA)',
        'value': roa,
        'unit': '%',
        'benchmark': '> 3%（基准）',
        'score': _score_margin(roa, ROA_LOW, ROA_HIGH),
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

    return metrics


def _calculate_cashflow_metrics(f: Dict, fp: Dict) -> Dict:
    """计算现金流指标"""
    metrics = {}

    net_profit        = f.get('net_profit', 0) or 0
    operating_cashflow = f.get('operating_cashflow') or 0
    cash_from_sales    = f.get('cash_from_sales', 0) or 0
    revenue            = f.get('revenue', 0) or 0
    current_liab       = f.get('current_liabilities', 0) or 0
    cash               = f.get('cash', 0) or 0

    # 若无现金流量表但有利润数据，用间接法估算经营现金流
    cf_is_estimated = False
    if operating_cashflow == 0 and net_profit:
        depreciation = f.get('depreciation', 0) or 0
        amortization = f.get('amortization', 0) or (f.get('long_term_deferred_expense', 0) or 0) * 0.1

        def _change(key):
            """计算两期变动（当期 - 上期），正值表示增加"""
            curr = f.get(key, 0) or 0
            prev = (fp.get(key, 0) or 0) if fp else 0
            return curr - prev

        # 经营性资产变动（增加=现金流出，取负号）
        ar_change = _change('accounts_receivable')       # 应收增加 → 现金流出
        inv_change = _change('inventory')                 # 存货增加 → 现金流出
        prepaid_change = _change('prepaid_accounts')      # 预付增加 → 现金流出
        other_recv_change = _change('other_receivables')  # 其他应收增加 → 现金流出

        # 经营性负债变动（增加=现金流入）
        ap_change = _change('accounts_payable')           # 应付增加 → 现金流入
        advance_change = _change('advance_receipts')      # 预收增加 → 现金流入
        wages_change = _change('wages_payable')           # 应付薪酬增加 → 现金流入
        tax_change = _change('taxes_payable')             # 应交税金增加 → 现金流入
        other_pay_change = _change('other_payables')      # 其他应付增加 → 现金流入

        estimated_cf = (net_profit
                        + depreciation + amortization
                        - ar_change - inv_change - prepaid_change - other_recv_change
                        + ap_change + advance_change + wages_change + tax_change + other_pay_change)
        operating_cashflow = estimated_cf
        cf_is_estimated = True

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

    return metrics


def _calculate_operations_metrics(f: Dict, fp: Optional[Dict] = None) -> Dict:
    """计算营运能力指标"""
    metrics = {}

    revenue            = f.get('revenue', 0) or 0
    total_assets       = f.get('total_assets', 0) or 0
    accounts_receivable = f.get('accounts_receivable', 0) or 0
    deposit_out        = f.get('deposit_out', 0) or 0
    inventory          = f.get('inventory', 0) or 0

    # 应收账款周转率（担保公司：应收款含存出保证金）
    effective_ar = accounts_receivable + deposit_out
    ar_turnover = safe_div(revenue, effective_ar) if effective_ar > 0 else None
    metrics['ar_turnover'] = {
        'label': '应收/保证金周转率',
        'value': ar_turnover,
        'unit': '次/年',
        'benchmark': '越高越好',
        'score': _score_turnover(ar_turnover, 1, 3),
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

    # 担保专项：净资本充足率
    capital_adequacy = safe_div(f.get('paid_in_capital', 0) or 0, total_assets)
    metrics['capital_adequacy'] = {
        'label': '净资本充足率',
        'value': capital_adequacy,
        'unit': '%',
        'benchmark': '担保公司：≥ 40%',
        'score': _score_margin(capital_adequacy, 0.3, 0.6),
        'triggered_rules': [],
    }

    # ── 新增：存货周转天数 ──
    cost_of_sales = f.get('cost_of_sales', 0) or 0
    inventory_turnover = safe_div(cost_of_sales, inventory) if inventory > 0 else None
    inventory_days = safe_div(365, inventory_turnover) if inventory_turnover else None
    metrics['inventory_days'] = {
        'label': '存货周转天数',
        'value': inventory_days,
        'unit': '天',
        'benchmark': '行业差异大',
        'score': _create_sigmoid_scorer(90.0, 3.0, direction='lower_is_better', default=50.0)(inventory_days),
        'triggered_rules': get_triggered_rules('inventory_growth', inventory_days) if inventory_days is not None and fp else [],
    }

    # ── 新增：存货增长率（需要上期数据） ──
    if fp:
        inv_prev = fp.get('inventory', 0) or 0
        if inv_prev > 0 and inventory > 0:
            inv_growth = (inventory - inv_prev) / inv_prev
            metrics['inventory_growth'] = {
                'label': '存货增长率',
                'value': inv_growth,
                'unit': '%',
                'benchmark': '< 30%（正常）',
                'score': max(0, 100 - abs(inv_growth) * 200) if abs(inv_growth) > 0.3 else 85,
                'triggered_rules': get_triggered_rules('inventory_growth', inv_growth),
                'trend_type': True,
            }

    # ── 新增：应收增速与收入增速差距（需要上期数据） ──
    if fp:
        ar_prev = fp.get('accounts_receivable', 0) or 0
        rev_prev = fp.get('revenue', 0) or 0
        if ar_prev > 0 and rev_prev > 0 and revenue > 0:
            ar_growth = (accounts_receivable - ar_prev) / ar_prev
            rev_growth = (revenue - rev_prev) / rev_prev
            ar_rev_gap = ar_growth - rev_growth
            metrics['ar_revenue_growth_gap'] = {
                'label': '应收增速-收入增速差距',
                'value': ar_rev_gap,
                'unit': '%',
                'benchmark': '< 0（应收增速低于收入）',
                'score': max(0, 100 - ar_rev_gap * 150) if ar_rev_gap > 0 else min(100, 80 + abs(ar_rev_gap) * 100),
                'triggered_rules': get_triggered_rules('ar_revenue_growth_gap', ar_rev_gap),
                'trend_type': True,
            }

    return metrics


def _calculate_tax_compliance_metrics(f: Dict, tax: Dict) -> Dict:
    """计算税务合规指标"""
    metrics = {}

    revenue   = f.get('revenue', 0) or 0
    vat_sales = tax.get('vat_taxable_sales', 0)

    if vat_sales and revenue and vat_sales > 0:
        vat_gap = abs(vat_sales - revenue) / revenue
        metrics['vat_revenue_gap'] = {
            'label': '增值税收入-财报收入差异率',
            'value': vat_gap,
            'unit': '%',
            'benchmark': '< 15%（正常）',
            'score': max(0, 100 - vat_gap * VAT_GAP_PENALTY_FACTOR),
            'triggered_rules': get_triggered_rules('vat_revenue_gap', vat_gap),
        }
    else:
        metrics['vat_revenue_gap'] = {
            'label': '增值税申报核验',
            'value': None,
            'unit': '',
            'benchmark': '无增值税申报数据',
            'score': 60,
            'triggered_rules': [],
            'note': '未提供增值税申报表，无法核验收入一致性',
        }

    return metrics


def _calculate_fraud_alerts(f: Dict, fp: Optional[Dict]) -> Dict:
    """计算造假预警指标"""
    metrics = {}

    # Beneish M-Score
    m_result = _calculate_m_score(f, fp if fp else None)
    if m_result is not None:
        m_score = m_result['m_score']
        metrics['m_score'] = {
            'label': 'Beneish M-Score（造假预警）',
            'value': m_score,
            'unit': '',
            'benchmark': '< -1.78（安全）',
            'score': 100 if m_score < MSCORE_SAFE else (50 if m_score < MSCORE_DANGER else 0),
            'triggered_rules': get_triggered_rules('m_score', m_score),
            # 8 因子详情
            'DSRI': m_result['DSRI'],
            'GMI': m_result['GMI'],
            'AQI': m_result['AQI'],
            'SGI': m_result['SGI'],
            'DEPI': m_result['DEPI'],
            'SGAI': m_result['SGAI'],
            'TATA': m_result['TATA'],
            'LVGI': m_result['LVGI'],
        }

    return metrics


# ─────────────────────────────────────────────
# 主指标计算（重构后）
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

    # 数据完整性校验
    metrics.update(_calculate_data_validation(f))

    # 偿债能力
    metrics.update(_calculate_solvency_metrics(f))

    # 盈利能力
    metrics.update(_calculate_profitability_metrics(f, fp))

    # 现金流
    metrics.update(_calculate_cashflow_metrics(f, fp))

    # 营运能力
    metrics.update(_calculate_operations_metrics(f, fp))

    # 税务合规
    metrics.update(_calculate_tax_compliance_metrics(f, tax))

    # 跨期趋势分析
    if fp:
        trend_metrics = _calculate_trend_metrics(f, fp)
        metrics.update(trend_metrics)

    # 造假预警
    metrics.update(_calculate_fraud_alerts(f, fp))

    return metrics


# ─────────────────────────────────────────────
# 跨期趋势指标
# ─────────────────────────────────────────────

def _calculate_trend_metrics(f_new: Dict, f_old: Dict) -> Dict:
    """
    基于两期数据计算趋势指标

    重要：f_new / f_old 来自 flatten_financial(use_annualized=True)，
    季报的流量指标（收入、利润等）已被年化，无需再次乘因子。
    """
    metrics = {}

    new_factor = f_new.get('_annualization_factor', 1.0)

    def pct(key: str, annualize_new: bool = False, annualize_factor: int = 4) -> Optional[float]:
        """计算增长率"""
        new_v = f_new.get(key)
        old_v = f_old.get(key)
        if new_v is None or old_v is None or abs(old_v) < 1:
            return None
        if annualize_new and new_factor <= 1.0:
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
            'score': _score_growth(asset_growth, GROWTH_NEUTRAL, GROWTH_GOOD),
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

    # 收入趋势
    rev_new = f_new.get('revenue')
    rev_old = f_old.get('revenue')
    if rev_new is not None and rev_old is not None and rev_old > 0:
        rev_growth_yoy = (rev_new - rev_old) / rev_old
        if new_factor > 1.0:
            label = f'收入年化增速（Q{int(12/new_factor)}折年 vs 全年）'
        else:
            label = '收入同比增速'
        metrics['revenue_growth_yoy'] = {
            'label': label,
            'value': rev_growth_yoy,
            'unit': '%',
            'benchmark': '> 10%（良好）',
            'score': _score_growth(rev_growth_yoy, 0, 0.2),
            'triggered_rules': [],
            'trend_type': True,
        }

    # 利润变化
    np_new = f_new.get('net_profit')
    np_old = f_old.get('net_profit')
    if np_new is not None and np_old is not None and np_old > 0:
        profit_growth = (np_new - np_old) / np_old
        if new_factor > 1.0:
            label = f'利润年化增速（Q{int(12/new_factor)}折年 vs 全年）'
        else:
            label = '利润同比增速'
        metrics['profit_growth_yoy'] = {
            'label': label,
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
        'score': max(0, 70 - abs(dr_change) * DEBT_RATIO_CHANGE_PENALTY) if dr_change > 0 else min(100, 80 + abs(dr_change) * DEBT_RATIO_CHANGE_PENALTY),
        'triggered_rules': [],
        'trend_type': True,
    }

    # 应收账款变化
    deposit_change = pct('deposit_out')
    if deposit_change is not None:
        metrics['deposit_out_change'] = {
            'label': '存出保证金变动率',
            'value': deposit_change,
            'unit': '%',
            'benchmark': '< 30%（稳定）',
            'score': max(0, 80 - abs(deposit_change) * DEPOSIT_CHANGE_PENALTY) if abs(deposit_change) > DEPOSIT_CHANGE_THRESHOLD else 85,
            'triggered_rules': [],
            'trend_type': True,
        }

    # 跨期异常检测
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
    返回异常度 0~1（0=正常，1=严重异常）
    """
    anomaly_scores = []

    # 检查总资产是否出现大幅下降
    ta_new = f_new.get('total_assets', 0) or 0
    ta_old = f_old.get('total_assets', 0) or 0
    if ta_old > 0 and ta_new < ta_old * ASSET_DECLINE_THRESHOLD:
        anomaly_scores.append(0.8)
    elif ta_old > 0 and ta_new > 0:
        anomaly_scores.append(0.0)

    # 利润与收入增长方向是否一致
    rev_new = f_new.get('revenue') or 0
    rev_old = f_old.get('revenue') or 0
    np_new = f_new.get('net_profit') or 0
    np_old = f_old.get('net_profit') or 0
    if rev_old > 0 and np_old > 0:
        rev_dir = 1 if rev_new > rev_old else -1
        np_dir = 1 if np_new > np_old else -1
        if rev_dir != np_dir:
            anomaly_scores.append(ANOMALY_SCORE_INCONSISTENT)
        else:
            anomaly_scores.append(0.0)

    return round(sum(anomaly_scores) / max(len(anomaly_scores), 1), 3) if anomaly_scores else None


# ─────────────────────────────────────────────
# Beneish M-Score（完整 8 因子实现）
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
        sga   = (f.get('selling_expense') or 0) + (f.get('admin_expense') or 0)
        tl    = f.get('total_liabilities') or 0
        te    = f.get('total_equity') or (ta - tl)
        ocf   = f.get('operating_cashflow') or 0
        np    = f.get('net_profit') or 0

        if rev <= 0 or ta <= 0:
            return None

        gp    = rev - cost
        gross_margin = gp / rev

        # TATA: 应计利润比率
        tata = (np - ocf) / ta

        if f_prev:
            rev0  = f_prev.get('revenue') or 1
            ar0   = f_prev.get('accounts_receivable') or 0
            cost0 = f_prev.get('cost_of_sales') or 0
            ta0   = f_prev.get('total_assets') or 1
            fa0   = f_prev.get('fixed_assets') or f_prev.get('fixed_assets_gross') or 0
            depr0 = f_prev.get('depreciation') or 0
            sga0  = (f_prev.get('selling_expense') or 0) + (f_prev.get('admin_expense') or 0)
            tl0   = f_prev.get('total_liabilities') or 0
            te0   = f_prev.get('total_equity') or (ta0 - tl0)
            gp0   = rev0 - cost0
            gm0   = gp0 / rev0 if rev0 else 0

            # DSRI: 应收账款指数
            dsri = (ar / rev) / (ar0 / rev0) if ar0 > 0 else (ar / rev + 1)

            # GMI: 毛利率指数
            gmi = gm0 / gross_margin if gross_margin > 0 else 1.0

            # AQI: 资产质量指数（Beneish 原始定义：1 - (长期资产净值/总资产)）
            # 长期资产 = 固定资产 + 无形资产 + 长期待摊费用
            lt_assets = fa + (f.get('intangible_assets') or 0) + (f.get('long_term_deferred_expense') or 0)
            lt_assets0 = fa0 + (f_prev.get('intangible_assets') or 0) + (f_prev.get('long_term_deferred_expense') or 0)
            aqi_curr = 1 - lt_assets / ta
            aqi_prev = 1 - lt_assets0 / ta0
            aqi = aqi_curr / aqi_prev if aqi_prev > 0 else 1.0

            # SGI: 营收增长指数
            sgi = rev / rev0 if rev0 > 0 else 1.0

            # DEPI: 折旧指数
            depr = f.get('depreciation') or 0
            dep_rate0 = depr0 / (fa0 + depr0) if (fa0 + depr0) > 0 else 0
            dep_rate  = depr / (fa + depr) if (fa + depr) > 0 else dep_rate0
            depi = dep_rate0 / dep_rate if dep_rate > 0 else 1.0

            # SGAI: 销售管理费用指数
            sgai = (sga / rev) / (sga0 / rev0) if (sga0 > 0 and rev0 > 0) else 1.0

            # LVGI: 杠杆指数
            lev_curr = tl / (tl + te) if (tl + te) > 0 else 0
            lev_prev = tl0 / (tl0 + te0) if (tl0 + te0) > 0 else 0
            lvgi = lev_curr / lev_prev if lev_prev > 0 else 1.0

        else:
            # 无上期数据：使用保守中性值
            dsri = (ar / rev) / ASSUMED_AR_REVENUE_RATIO if rev > 0 else 1.0
            dsri = min(dsri, DSRI_CAP)
            gmi  = 1.0
            aqi  = 1.0
            sgi  = 1.0
            depi = 1.0
            sgai = 1.0
            lvgi = 1.0

        # 计算 M-Score
        m = (BENEISH_COEFFICIENTS['intercept']
             + BENEISH_COEFFICIENTS['dsri'] * dsri
             + BENEISH_COEFFICIENTS['gmi'] * gmi
             + BENEISH_COEFFICIENTS['aqi'] * aqi
             + BENEISH_COEFFICIENTS['sgi'] * sgi
             + BENEISH_COEFFICIENTS['depi'] * depi
             + BENEISH_COEFFICIENTS['sgai'] * sgai
             + BENEISH_COEFFICIENTS['tata'] * tata
             + BENEISH_COEFFICIENTS['lvgi'] * lvgi)

        return {
            'm_score': round(m, 3),
            'DSRI': round(dsri, 4),
            'GMI': round(gmi, 4),
            'AQI': round(aqi, 4),
            'SGI': round(sgi, 4),
            'DEPI': round(depi, 4),
            'SGAI': round(sgai, 4),
            'TATA': round(tata, 4),
            'LVGI': round(lvgi, 4),
        }
    except Exception:
        return None


# ─────────────────────────────────────────────
# 评分函数（0-100，sigmoid 平滑）
# ─────────────────────────────────────────────

def _create_sigmoid_scorer(center: float, steepness: float = 8.0,
                           direction: str = 'higher_is_better',
                           cap: Optional[float] = None,
                           default: float = 50.0):
    """评分函数工厂"""
    def scorer(v: Optional[float]) -> float:
        if v is None:
            return default
        if cap is not None:
            v = min(v, cap)
        return _sigmoid_score(v, center=center, steepness=steepness, direction=direction)
    return scorer


# 使用工厂创建评分函数
_score_current_ratio = _create_sigmoid_scorer(CURRENT_RATIO_CENTER, CURRENT_RATIO_STEEPNESS, cap=CURRENT_RATIO_CAP)
_score_quick_ratio = _create_sigmoid_scorer(QUICK_RATIO_CENTER, QUICK_RATIO_STEEPNESS, cap=QUICK_RATIO_CAP)
_score_debt_ratio = _create_sigmoid_scorer(DEBT_RATIO_CENTER, DEBT_RATIO_STEEPNESS, direction='lower_is_better')
_score_icr = _create_sigmoid_scorer(ICR_CENTER, ICR_STEEPNESS, cap=ICR_CAP, default=60.0)
_score_cash_ratio = _create_sigmoid_scorer(CASH_RATIO_CENTER, CASH_RATIO_STEEPNESS, cap=CASH_RATIO_CAP)
_score_ar_days_guarantee = _create_sigmoid_scorer(365.0, 2.0, direction='lower_is_better', default=60.0)


def _score_margin(v: Optional[float], low: float, high: float) -> float:
    """通用利润率/比率评分"""
    if v is None:
        return 50
    center = (low + high) / 2.0
    return _sigmoid_score(v, center=center, steepness=8.0)


def _score_cashflow(v: Optional[float]) -> float:
    """经营净现金流评分"""
    if v is None:
        return 50
    v_norm = v / 1e4  # 用万元归一化
    return _sigmoid_score(v_norm, center=0.0, steepness=0.3)


def _score_tax_rate(v: Optional[float]) -> float:
    """有效税率评分"""
    if v is None:
        return 60
    deviation = abs(v - TAX_RATE_OPTIMAL)
    return max(0.0, round(100.0 - deviation * TAX_RATE_PENALTY, 1))


def _score_turnover(v: Optional[float], low: float, high: float) -> float:
    """周转率评分"""
    if v is None:
        return 50
    center = (low + high) / 2.0
    return _sigmoid_score(v, center=center, steepness=TURNOVER_STEEPNESS)


def _score_growth(v: Optional[float], low: float, high: float) -> float:
    """增长率评分"""
    if v is None:
        return 50
    center = (low + high) / 2.0 if (low + high) != 0 else 0.1
    return _sigmoid_score(v, center=center, steepness=GROWTH_STEEPNESS)


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
    """计算单个维度的得分"""
    keys = DIMENSION_METRIC_MAP.get(dimension, [])
    scores = [metrics[k]['score'] for k in keys if k in metrics and metrics[k].get('score') is not None]
    if not scores:
        return 60.0
    return round(sum(scores) / len(scores), 1)


def compute_total_score(metrics: Dict, industry: str = '通用') -> Dict:
    """计算综合评分"""
    weights = INDUSTRY_WEIGHTS.get(industry, INDUSTRY_WEIGHTS['通用'])
    dim_scores = {}
    for dim in weights:
        dim_scores[dim] = compute_dimension_score(metrics, dim)

    # 造假预警一票否决
    m_score_val = metrics.get('m_score', {}).get('value')
    veto = m_score_val is not None and m_score_val > MSCORE_DANGER

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
