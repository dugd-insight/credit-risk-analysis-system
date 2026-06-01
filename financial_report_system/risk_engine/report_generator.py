# -*- coding: utf-8 -*-
"""
授信决策报告 HTML 生成器 v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
新增 v3.0：
  - 三表勾稽校验结果（期末现金一致性、会计恒等式、利润含金量）
  - Beneish M-Score 详细计算过程
  - 知识库评判完整展示（监管依据、行业基准、规则触发详情）
  - 资产负债表/利润表/现金流量表完整展示
  - 期间类型年化说明
  - 行业基准对照
"""

import os
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple


RISK_LEVEL_MAP = {
    'CRITICAL': ('极高风险', '#7a1010', '#fde8e8'),
    'HIGH':     ('高风险',   '#992d20', '#fff0ec'),
    'MEDIUM':   ('中等风险', '#854f0b', '#fef3e2'),
    'LOW':      ('低风险',   '#1a6b3a', '#eaf3de'),
}

GRADE_COLOR = {
    'green':  ('#1a6b3a', '#eaf3de', '#c0dd97'),
    'yellow': ('#7a5c00', '#fef9e7', '#fac775'),
    'orange': ('#854f0b', '#fff0ec', '#f0997b'),
    'red':    ('#7a1010', '#fde8e8', '#f09595'),
}


def _fmt(v: Optional[float], unit: str = '', pct: bool = False) -> str:
    if v is None:
        return 'N/A'
    if pct or unit == '%':
        return f'{v * 100:.2f}%'
    if unit == '元':
        if abs(v) >= 1e8:
            return f'{v/1e8:.4f} 亿元'
        if abs(v) >= 1e4:
            return f'{v/1e4:.2f} 万元'
        return f'{v:.2f} 元'
    if unit in ('倍', '次/年', '天'):
        return f'{v:.2f} {unit}'
    return f'{v:.3f}'


def _fmt_wan(v: Optional[float]) -> str:
    """万元格式化"""
    if v is None:
        return 'N/A'
    return f'{v/1e4:,.2f} 万元'


def _score_bar(score: float, width: int = 120) -> str:
    pct = max(0, min(100, score))
    color = '#1D9E75' if pct >= 75 else ('#EF9F27' if pct >= 60 else ('#D85A30' if pct >= 40 else '#A32D2D'))
    return (
        f'<div style="display:inline-flex;align-items:center;gap:8px">'
        f'<div style="width:{width}px;height:8px;background:#eee;border-radius:4px;overflow:hidden">'
        f'<div style="width:{int(pct)}%;height:100%;background:{color};border-radius:4px"></div></div>'
        f'<span style="font-size:13px;font-weight:500;color:{color}">{score:.0f}分</span>'
        f'</div>'
    )


def _rule_tag(rule: Dict) -> str:
    """知识库规则标签 - 完整展示监管依据"""
    lvl = rule.get('risk_level', 'LOW')
    label, text_color, bg_color = RISK_LEVEL_MAP.get(lvl, RISK_LEVEL_MAP['LOW'])
    rid = rule.get('id', '')
    name = rule.get('name', '')
    regulation = rule.get('regulation', '')
    standard = rule.get('standard', '')
    suggestion = rule.get('suggestion', '')
    benchmark = rule.get('benchmark', '')
    
    return f'''
<div style="margin:6px 0;padding:10px 12px;background:{bg_color};border-left:3px solid {text_color};
     border-radius:0 6px 6px 0;font-size:12px">
  <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
    <span style="background:{text_color};color:#fff;padding:1px 6px;border-radius:3px;
          font-size:11px;font-weight:500">{label}</span>
    <span style="font-weight:500;color:{text_color}">[{rid}] {name}</span>
  </div>
  <div style="color:#555;line-height:1.7">
    <div><b>监管依据：</b>{regulation}</div>
    <div><b>适用准则：</b>{standard}</div>
    {f'<div><b>行业基准：</b>{benchmark}</div>' if benchmark else ''}
    <div><b>授信建议：</b>{suggestion}</div>
  </div>
</div>'''


def _build_consistency_check_html(three_stmt: Dict, consistency_result: List[Dict]) -> str:
    """构建三表勾稽校验结果"""
    if not consistency_result:
        return ''
    
    items_html = ''
    for item in consistency_result:
        result = item.get('result', False)
        if result:
            icon, color, bg = '✅', '#1a6b3a', '#eaf3de'
        else:
            icon, color, bg = '❌', '#7a1010', '#fde8e8'

        items_html += f'''
        <div style="margin:8px 0;padding:10px 12px;background:{bg};border-radius:6px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">
                <span style="font-size:16px">{icon}</span>
                <span style="font-weight:500;color:{color}">{item.get('check', '')}</span>
            </div>
            <div style="font-size:12px;color:#555">{item.get('detail', '')}</div>
            {f'<div style="margin-top:4px;font-size:11px;color:#888">校验逻辑: {item.get("theory", "")}</div>' if item.get('theory') else ''}
        </div>'''
    
    return f'''
<div class="card" style="border-left:4px solid #4F46E5">
  <h2>🔍 三表勾稽校验（资产负债表 / 利润表 / 现金流量表）</h2>
  <div style="margin-top:12px">{items_html}</div>
</div>'''


def _build_mscore_detail_html(metrics: Dict) -> str:
    """构建 Beneish M-Score 详细计算"""
    ms = metrics.get('m_score', {})
    if not ms or ms.get('value') is None:
        return ''
    
    value = ms.get('value', 0)
    interpretation = '财务造假可能性低' if value < -2.22 else ('财务造假可能性高' if value > -1.78 else '无法判断')
    interp_color = '#1a6b3a' if value < -2.22 else ('#7a1010' if value > -1.78 else '#854f0b')
    
    # 各因子详情
    factors = [
        ('DSRI', '应收账款指数', ms.get('DSRI')),
        ('GMI', '毛利率指数', ms.get('GMI')),
        ('AQI', '资产质量指数', ms.get('AQI')),
        ('SGI', '营收增长指数', ms.get('SGI')),
        ('DEPI', '折旧指数', ms.get('DEPI')),
        ('SGAI', '销管费用指数', ms.get('SGAI')),
        ('TATA', '应计利润比率', ms.get('TATA')),
        ('LVGI', '财务杠杆指数', ms.get('LVGI')),
    ]
    
    factors_html = ''
    for fid, fname, fval in factors:
        if fval is None:
            continue
        # 判断因子是否异常（偏离1.0较多）
        is_abnormal = fval > 1.1 or fval < 0.9
        color = '#D85A30' if is_abnormal else '#555'
        arrow = '↑' if fval > 1.0 else ('↓' if fval < 1.0 else '→')
        factors_html += f'''
        <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:0.5px solid #f0f0f0">
            <span style="font-weight:500;color:#333">{fid} - {fname}</span>
            <span style="color:{color};font-weight:500">{arrow} {fval:.4f}</span>
        </div>'''
    
    return f'''
<div class="card" style="border-left:4px solid #7C3AED">
  <h2>🎯 Beneish M-Score 财务造假预警（8因子模型）</h2>
  <div style="display:grid;grid-template-columns:1fr 2fr;gap:24px;margin-top:12px">
    <div style="text-align:center;padding:20px;background:#f8f9fa;border-radius:12px">
      <div style="font-size:36px;font-weight:600;color:{interp_color}">{value:.2f}</div>
      <div style="font-size:14px;margin-top:8px;color:{interp_color}">{interpretation}</div>
      <div style="font-size:11px;color:#888;margin-top:8px">
        <div>模型阈值说明：</div>
        <div>M-Score &lt; -2.22 → 正常</div>
        <div>M-Score &gt; -1.78 → 高度怀疑</div>
      </div>
    </div>
    <div style="background:#fff;border:0.5px solid #e5e7eb;border-radius:8px;padding:12px">
      <div style="font-weight:500;margin-bottom:8px;color:#333">各因子详情</div>
      {factors_html}
    </div>
  </div>
</div>'''


def _build_knowledge_base_section(metrics: Dict) -> str:
    """构建知识库评判完整展示"""
    all_rules = []
    for key, m in metrics.items():
        for rule in m.get('triggered_rules', []):
            all_rules.append({
                'metric_label': m.get('label', key),
                'metric_value': m.get('value'),
                'metric_unit': m.get('unit', ''),
                'rule': rule
            })
    
    if not all_rules:
        return '''
<div class="card" style="border-left:4px solid #1a6b3a">
  <h2>📋 知识库评判结果</h2>
  <div style="padding:20px;text-align:center;color:#1a6b3a;font-size:14px">
    ✅ 未触发任何风险预警规则，企业财务状况良好
  </div>
</div>'''
    
    # 按风险等级分组
    by_level = {'CRITICAL': [], 'HIGH': [], 'MEDIUM': [], 'LOW': []}
    for item in all_rules:
        lvl = item['rule'].get('risk_level', 'LOW')
        if lvl in by_level:
            by_level[lvl].append(item)
    
    level_names = {
        'CRITICAL': ('🔴 极高风险', '#7a1010'),
        'HIGH': ('🟠 高风险', '#992d20'),
        'MEDIUM': ('🟡 中等风险', '#854f0b'),
        'LOW': ('🟢 低风险', '#1a6b3a'),
    }
    
    sections_html = ''
    for lvl in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
        items = by_level[lvl]
        if not items:
            continue
        name, color = level_names[lvl]
        
        items_html = ''
        for item in items:
            v = item['metric_value']
            unit = item['metric_unit']
            rule = item['rule']
            
            items_html += f'''
            <div style="margin:8px 0;padding:10px 12px;background:#fafafa;border-radius:6px">
                <div style="font-weight:500;color:#333;margin-bottom:4px">
                    {item['metric_label']}: {_fmt(v, unit)} 
                    <span style="color:#888;font-weight:normal">（触发 [{rule.get('id','')}]）</span>
                </div>
                <div style="font-size:12px;color:#555">{_rule_tag(rule)}</div>
            </div>'''
        
        sections_html += f'''
        <div style="margin-bottom:16px">
            <div style="font-weight:600;font-size:14px;color:{color};margin-bottom:8px">{name} ({len(items)}条)</div>
            {items_html}
        </div>'''
    
    return f'''
<div class="card" style="border-left:4px solid #DC2626">
  <h2>📋 知识库评判结果（共触发 {len(all_rules)} 条规则）</h2>
  {sections_html}
</div>'''


def _build_balance_sheet_table(fin: Dict) -> str:
    """构建资产负债表
    
    注意：键名必须与 file_parser.py 的 ASSET_MAP/LIABILITY_MAP 输出保持一致
    ASSET_MAP 输出: cash, short_term_investment, notes_receivable, accounts_receivable,
                    prepaid_accounts, other_receivables, inventory, current_assets, 
                    fixed_assets, intangible_assets, total_assets, deposit_out, 
                    long_term_deferred_expense 等
    LIABILITY_MAP 输出: short_term_loans, notes_payable, accounts_payable, advance_receipts,
                      wages_payable, taxes_payable, other_payables, deposit_in, current_liabilities,
                      long_term_loans, non_current_liabilities, total_liabilities,
                      paid_in_capital, capital_reserve, surplus_reserve, retained_earnings, 
                      total_equity, subsidy_fund 等
    """
    items = [
        ('资产类', [
            ('货币资金', 'cash'),
            ('短期投资', 'short_term_investment'),
            ('应收票据', 'notes_receivable'),
            ('应收账款', 'accounts_receivable'),
            ('预付款项', 'prepaid_accounts'),
            ('其他应收款', 'other_receivables'),
            ('存货', 'inventory'),
            ('流动资产合计', 'current_assets'),
            ('固定资产', 'fixed_assets'),
            ('无形资产', 'intangible_assets'),
            ('长期待摊费用', 'long_term_deferred_expense'),  # 担保公司专用
            ('非流动资产合计', 'long_term_equity_inv'),
            ('资产总计', 'total_assets'),
        ]),
        ('负债类', [
            ('短期借款', 'short_term_loans'),
            ('应付票据', 'notes_payable'),
            ('应付账款', 'accounts_payable'),
            ('预收款项', 'advance_receipts'),
            ('应付职工薪酬', 'wages_payable'),
            ('应交税费', 'taxes_payable'),
            ('其他应付款', 'other_payables'),
            ('存入保证金', 'deposit_in'),  # 担保公司专用
            ('流动负债合计', 'current_liabilities'),
            ('长期借款', 'long_term_loans'),
            ('非流动负债合计', 'non_current_liabilities'),
            ('负债合计', 'total_liabilities'),
        ]),
        ('所有者权益', [
            ('实收资本', 'paid_in_capital'),
            ('资本公积', 'capital_reserve'),
            ('盈余公积', 'surplus_reserve'),
            ('未分配利润', 'retained_earnings'),
            ('所有者权益合计', 'total_equity'),
        ]),
    ]
    
    def build_rows(category_items):
        rows = ''
        for label, key in category_items:
            v = fin.get(key)
            is_total = '合计' in label or '总计' in label
            rows += f'''
            <tr>
                <td style="padding:5px 8px;font-size:13px;border:1px solid #e5e7eb;{'font-weight:600;background:#f8f9fa' if is_total else ''}">{label}</td>
                <td style="padding:5px 8px;font-size:13px;text-align:right;border:1px solid #e5e7eb;{'font-weight:600;background:#f8f9fa' if is_total else ''}">{_fmt_wan(v)}</td>
            </tr>'''
        return rows
    
    html = ''
    for category, category_items in items:
        html += f'''
        <div style="margin-bottom:12px">
            <div style="font-weight:600;font-size:13px;color:#333;margin-bottom:4px;padding-bottom:4px;border-bottom:2px solid #4F46E5">{category}</div>
            <table style="width:100%;border-collapse:collapse">
                <tbody>{build_rows(category_items)}</tbody>
            </table>
        </div>'''
    
    return html


def _build_income_statement_table(fin: Dict) -> str:
    """构建利润表
    
    注意：键名必须与 file_parser.py 的 INCOME_MAP 输出保持一致
    INCOME_MAP 输出: revenue, cost_of_sales, gross_profit, tax_and_surcharges, business_tax,
                    selling_expense, admin_expense, finance_cost, investment_income,
                    operating_profit, non_operating_income, non_operating_expense,
                    profit_before_tax, income_tax, net_profit
    """
    items = [
        ('营业收入', 'revenue'),
        ('营业成本', 'cost_of_sales'),
        ('税金及附加', 'tax_and_surcharges'),
        ('销售费用', 'selling_expense'),
        ('管理费用', 'admin_expense'),
        ('财务费用', 'finance_cost'),
        ('资产减值损失', 'asset_impairment_loss'),
        ('公允价值变动收益', 'fair_value_change_income'),
        ('投资收益', 'investment_income'),
        ('营业利润', 'operating_profit'),
        ('营业外收入', 'non_operating_income'),
        ('营业外支出', 'non_operating_expense'),
        ('利润总额', 'profit_before_tax'),
        ('所得税费用', 'income_tax'),
        ('净利润', 'net_profit'),
    ]
    
    rows = ''
    for label, key in items:
        v = fin.get(key)
        is_highlight = key in ['operating_profit', 'total_profit', 'net_profit', 'profit_before_tax']
        rows += f'''
        <tr>
            <td style="padding:5px 8px;font-size:13px;border:1px solid #e5e7eb;{'font-weight:600;color:#333;background:#f0fdf4' if is_highlight else ''}">{label}</td>
            <td style="padding:5px 8px;font-size:13px;text-align:right;border:1px solid #e5e7eb;{'font-weight:600;background:#f0fdf4' if is_highlight else ''}">{_fmt_wan(v)}</td>
        </tr>'''
    
    return rows


def _build_cash_flow_table(fin: Dict) -> str:
    """构建现金流量表
    
    注意：键名必须与 file_parser.py 的 CASHFLOW_MAP 输出保持一致
    CASHFLOW_MAP 输出: cash_from_sales, tax_refund, other_operating_cash_in, operating_inflow,
                     cash_paid_goods, cash_paid_staff, taxes_paid, other_operating_cash_out,
                     operating_outflow, operating_cashflow, cash_from_investment,
                     cash_from_invest_income, cash_from_asset_disposal, investing_cash_inflow,
                     cash_for_assets, cash_for_investment, investing_cash_outflow,
                     investing_cashflow, cash_from_borrowings, cash_from_equity,
                     financing_cash_inflow, cash_for_debt, cash_for_dividends,
                     financing_cash_outflow, financing_cashflow, net_cash_change,
                     cash_end, cash_begin
    """
    items = [
        ('销售商品、提供劳务收到的现金', 'cash_from_sales'),
        ('收到的税费返还', 'tax_refund'),
        ('收到其他与经营活动有关的现金', 'other_operating_cash_in'),
        ('经营活动现金流入小计', 'operating_inflow'),
        ('购买商品、接受劳务支付的现金', 'cash_paid_goods'),
        ('支付给职工以及为职工支付的现金', 'cash_paid_staff'),
        ('支付的各项税费', 'taxes_paid'),
        ('支付其他与经营活动有关的现金', 'other_operating_cash_out'),
        ('经营活动现金流出小计', 'operating_outflow'),
        ('经营活动产生的现金流量净额', 'operating_cashflow'),
        ('收回投资收到的现金', 'cash_from_investment'),
        ('取得投资收益收到的现金', 'cash_from_invest_income'),
        ('处置固定资产、无形资产收回的现金', 'cash_from_asset_disposal'),
        ('投资活动现金流入小计', 'investing_cash_inflow'),
        ('购建固定资产、无形资产支付的现金', 'cash_for_assets'),
        ('投资支付的现金', 'cash_for_investment'),
        ('投资活动现金流出小计', 'investing_cash_outflow'),
        ('投资活动产生的现金流量净额', 'investing_cashflow'),
        ('取得借款收到的现金', 'cash_from_borrowings'),
        ('筹资活动现金流入小计', 'financing_cash_inflow'),
        ('偿还债务支付的现金', 'cash_for_debt'),
        ('分配股利、利润或偿付利息支付的现金', 'cash_for_dividends'),
        ('筹资活动现金流出小计', 'financing_cash_outflow'),
        ('筹资活动产生的现金流量净额', 'financing_cashflow'),
        ('现金及现金等价物净增加额', 'net_cash_change'),
        ('期末现金及现金等价物余额', 'cash_end'),
    ]
    
    rows = ''
    for label, key in items:
        v = fin.get(key)
        is_highlight = key in ['operating_cashflow', 'investing_cashflow', 'financing_cashflow', 'net_cash_change', 'cash_end']
        rows += f'''
        <tr>
            <td style="padding:5px 8px;font-size:13px;border:1px solid #e5e7eb;{'font-weight:600;color:#333;background:#fef3c7' if is_highlight else ''}">{label}</td>
            <td style="padding:5px 8px;font-size:13px;text-align:right;border:1px solid #e5e7eb;{'font-weight:600;background:#fef3c7' if is_highlight else ''}">{_fmt_wan(v)}</td>
        </tr>'''
    
    return rows


def _build_file_list_html(file_list: List[str], three_stmt: Optional[Dict] = None) -> str:
    """构建文件清单HTML — 每个文件一张卡片，左右排列
    
    Args:
        file_list: 文件路径列表
        three_stmt: 三表数据（包含 sheet 信息）
    """
    if not file_list:
        return ''

    raw_sheets = three_stmt.get('raw_sheets', {}) if three_stmt else {}
    bs = three_stmt.get('balance_sheet', {}) if three_stmt else {}
    inc = three_stmt.get('income_statement', {}) if three_stmt else {}
    cf = three_stmt.get('cash_flow', {}) if three_stmt else {}

    def _sheet_type_tag(name: str) -> str:
        sn = name.lower()
        if '资产负债' in name or ('资产' in sn and '表' in sn):
            return '<span style="background:#dbeafe;color:#1d4ed8;padding:1px 5px;border-radius:3px;font-size:10px">资产负债表</span>'
        if '利润' in name:
            return '<span style="background:#dcfce7;color:#15803d;padding:1px 5px;border-radius:3px;font-size:10px">利润表</span>'
        if '现金流' in name or '现金流动' in name or '资金流量' in name:
            return '<span style="background:#fef3c7;color:#b45309;padding:1px 5px;border-radius:3px;font-size:10px">现金流量表</span>'
        return '<span style="background:#f3f4f6;color:#6b7280;padding:1px 5px;border-radius:3px;font-size:10px">其他</span>'

    # ── 构建每个文件的卡片 ──
    cards = ''
    total_fields = len(bs) + len(inc) + len(cf)

    for idx, f in enumerate(file_list):
        fname = os.path.basename(f)
        ext = f.lower().rsplit('.', 1)[-1] if '.' in f else ''
        fmt = ext.upper() if ext else '—'
        try:
            fsize = os.path.getsize(f)
            size_str = f'{fsize / 1024 / 1024:.1f} MB' if fsize >= 1048576 else f'{fsize / 1024:.0f} KB'
        except Exception:
            size_str = '—'

        # 该文件的 Sheet 列表（表格形式）
        sheet_rows = ''
        for sname, rows_data in raw_sheets.items():
            rows_count = len(rows_data)
            cols_count = max((len(row) for row in rows_data), default=0)
            tag = _sheet_type_tag(sname)
            sheet_rows += f'''<tr>
  <td style="padding:4px 8px;font-size:12px;border:1px solid #e5e7eb">{sname}</td>
  <td style="padding:4px 8px;font-size:12px;border:1px solid #e5e7eb;text-align:center">{tag}</td>
  <td style="padding:4px 8px;font-size:12px;border:1px solid #e5e7eb;text-align:center;color:#555">{rows_count} × {cols_count}</td>
</tr>'''

        sheet_table = ''
        if sheet_rows:
            sheet_table = f'''<table style="width:100%;border-collapse:collapse;margin-top:4px">
  <thead><tr style="background:#f0f0f0">
    <th style="padding:4px 8px;font-size:11px;text-align:left;border:1px solid #e5e7eb;color:#666">Sheet 名称</th>
    <th style="padding:4px 8px;font-size:11px;text-align:center;border:1px solid #e5e7eb;color:#666">类型</th>
    <th style="padding:4px 8px;font-size:11px;text-align:center;border:1px solid #e5e7eb;color:#666">行×列</th>
  </tr></thead>
  <tbody>{sheet_rows}</tbody>
</table>'''

        # 该文件提取的字段数
        fields_html = ''
        if total_fields > 0:
            fields_html = f'<div style="margin-top:6px;font-size:12px;color:#059669;font-weight:500">✅ 已提取 {total_fields} 个字段</div>'

        cards += f'''
<div style="flex:1;min-width:240px;background:#fafafa;border-radius:8px;border-left:3px solid #4F46E5;padding:10px 12px">
  <div style="display:flex;align-items:center;gap:6px;margin-bottom:8px">
    <span style="font-size:16px">📊</span>
    <span style="font-weight:600;font-size:14px;color:#222">{fname}</span>
    <span style="font-size:12px;color:#999">{fmt} · {size_str}</span>
  </div>
  {sheet_table}
  {fields_html}
</div>'''

    # ── 汇总标签 ──
    summary = ''
    if len(bs) > 0:
        summary += f'<span style="background:#dbeafe;color:#1d4ed8;padding:2px 8px;border-radius:4px;font-size:11px">资产 {len(bs)} 项</span> '
    if len(inc) > 0:
        summary += f'<span style="background:#dcfce7;color:#15803d;padding:2px 8px;border-radius:4px;font-size:11px">利润 {len(inc)} 项</span> '
    if len(cf) > 0:
        summary += f'<span style="background:#fef3c7;color:#b45309;padding:2px 8px;border-radius:4px;font-size:11px">现金流 {len(cf)} 项</span>'

    return f'''
<div class="card" style="border-left:4px solid #4F46E5">
  <h2>📁 输入文件清单（共 {len(file_list)} 个文件参与分析）{summary}</h2>
  <div style="display:flex;gap:12px;margin-top:10px;flex-wrap:wrap">{cards}</div>
</div>'''


def _build_industry_benchmark(industry: str) -> str:
    """构建行业基准对照表"""
    benchmarks = {
        '担保/金融服务': [
            ('流动比率', '1.0-2.0', '银保监流动性要求'),
            ('速动比率', '≥1.0', '短期偿债能力'),
            ('资产负债率', '≤70%', '杠杆控制'),
            ('担保放大倍数', '≤10倍', '监管上限'),
            ('净资产充足率', '≥40%', '资本充足'),
        ],
        '制造业': [
            ('流动比率', '1.2-2.0', '制造业标准'),
            ('速动比率', '≥0.8', '短期偿债'),
            ('资产负债率', '≤65%', '杠杆控制'),
            ('存货周转率', '≥4次', '运营效率'),
            ('毛利率', '≥15%', '盈利能力'),
        ],
        '零售/批发': [
            ('流动比率', '1.0-1.5', '零售标准'),
            ('速动比率', '≥0.5', '快速变现'),
            ('资产负债率', '≤60%', '杠杆控制'),
            ('存货周转率', '≥6次', '商品周转'),
        ],
        '通用': [
            ('流动比率', '≥1.5', '通用标准'),
            ('速动比率', '≥1.0', '短期偿债'),
            ('资产负债率', '≤70%', '杠杆控制'),
            ('净资产收益率', '≥5%', '盈利能力'),
        ],
    }
    
    items = benchmarks.get(industry, benchmarks['通用'])
    
    rows = ''
    for metric, value, desc in items:
        rows += f'''
        <tr>
            <td style="padding:6px 8px;font-size:12px">{metric}</td>
            <td style="padding:6px 8px;font-size:12px;text-align:center;font-weight:500">{value}</td>
            <td style="padding:6px 8px;font-size:12px;color:#666">{desc}</td>
        </tr>'''
    
    return f'''
<div class="card" style="border-left:4px solid #0891B2">
  <h2>📐 行业基准对照（{industry}）</h2>
  <table style="margin-top:8px;font-size:12px">
    <thead>
      <tr style="background:#f8f9fa">
        <th style="padding:8px;text-align:left">指标</th>
        <th style="padding:8px;text-align:center">参考区间</th>
        <th style="padding:8px;text-align:left">说明</th>
      </tr>
    </thead>
    <tbody>{rows}</tbody>
  </table>
</div>'''


def _build_period_type_info(periods: List[str], period_details: Dict) -> Tuple[str, str]:
    """构建期间类型标签和详情（紧凑版，适合表格内嵌）"""
    period_badges = ''
    period_type_info = ''

    type_icons = {
        'annual': ('📊', '#059669'),
        'quarterly': ('📈', '#2563EB'),
        'monthly': ('📅', '#7C3AED'),
        'unknown': ('❓', '#6B7280'),
    }

    for p in periods:
        d = period_details.get(p, {})
        pi = d.get('period_info', {})
        report_type = pi.get('report_type', 'unknown')
        confidence = pi.get('confidence', 0)

        icon, color = type_icons.get(report_type, type_icons['unknown'])
        period_badges += f'<span style="background:#EEF2FF;color:{color};padding:3px 10px;border-radius:12px;font-size:12px;margin-right:6px">{icon} {p}</span>'

        if report_type != 'unknown':
            ann_factor = pi.get('annualization_factor', 1.0)
            note = pi.get('note', '')
            ann_tag = f' <span style="color:#059669;font-size:11px">×{ann_factor:.1f}年化</span>' if ann_factor != 1.0 and report_type != 'annual' else ''
            period_type_info += f'<span style="color:{color};font-weight:500">{icon} {p}→{report_type.upper()}</span> <span style="color:#888;font-size:11px">({confidence:.0%})</span>{ann_tag}'

    return period_badges, period_type_info


def _build_analysis_notes_html(analysis_notes: Optional[List[str]]) -> str:
    """构建分析说明HTML"""
    if not analysis_notes:
        return ''

    notes_html = '\n'.join(f'<div style="color:#78350F;margin:4px 0;font-size:13px">• {n}</div>' for n in analysis_notes)
    return f'''
        <div style="margin:16px 0;padding:12px;background:#FEF3C7;border-radius:8px;border-left:4px solid #F59E0B">
            <div style="font-weight:600;color:#92400E;margin-bottom:8px">📋 分析说明</div>
            {notes_html}
        </div>'''


def _build_kpi_cards(fin: Dict, metrics: Dict, fin_prev: Optional[Dict], periods: List[str]) -> str:
    """构建核心KPI表格行"""
    latest_period = periods[-1] if periods else ''
    kpi_items = [
        ('total_assets',     '资产总额',       '元'),
        ('total_equity',     '所有者权益',     '元'),
        ('revenue',          '营业收入',       '元'),
        ('net_profit',       '净利润',         '元'),
        ('current_ratio',    '流动比率',       '倍'),
        ('debt_ratio',       '资产负债率',     '%'),
        ('roe',              'ROE',            '%'),
        ('gross_profit_margin', '毛利率',      '%'),
    ]

    rows = ''
    for key, label, unit in kpi_items:
        v = fin.get(key) if fin.get(key) is not None else metrics.get(key, {}).get('value')
        is_pct = unit == '%'
        val_str = _fmt(v, unit, pct=is_pct)

        trend_html = ''
        if fin_prev and key in fin_prev and v is not None:
            prev_v = fin_prev.get(key) or metrics.get(key, {}).get('value')
            if prev_v and abs(prev_v) > 1e-6:
                chg = (v - prev_v) / abs(prev_v)
                if chg > 0.01:
                    trend_html = f'<span style="color:#1D9E75;font-size:10px;margin-left:4px">↑{chg*100:.1f}%</span>'
                elif chg < -0.01:
                    trend_html = f'<span style="color:#D85A30;font-size:10px;margin-left:4px">↓{abs(chg)*100:.1f}%</span>'

        rows += f'''
        <tr>
          <td style="color:#888;padding:3px 0;width:80px">{label}</td>
          <td style="font-weight:500;padding:3px 0">{val_str}{trend_html}</td>
        </tr>'''

    return rows


def _build_alert_table(metrics: Dict) -> str:
    """构建风险预警表格"""
    all_alerts = []
    for key, m in metrics.items():
        for rule in m.get('triggered_rules', []):
            all_alerts.append((m['label'], rule))

    if not all_alerts:
        return '<tr><td colspan="4" style="text-align:center;padding:20px;color:#888;font-size:13px">✅ 未触发任何风险预警规则</td></tr>'

    alert_html = ''
    for metric_label, rule in all_alerts:
        lvl = rule.get('risk_level', 'LOW')
        _, tc, bc = RISK_LEVEL_MAP.get(lvl, RISK_LEVEL_MAP['LOW'])
        alert_html += f'''
<tr>
  <td style="padding:8px;border-bottom:0.5px solid #eee;font-size:12px">{metric_label}</td>
  <td style="padding:8px;border-bottom:0.5px solid #eee">
    <span style="background:{bc};color:{tc};padding:1px 7px;border-radius:10px;font-size:11px;font-weight:500">
      {RISK_LEVEL_MAP.get(lvl,('','',''))[0]}</span></td>
  <td style="padding:8px;border-bottom:0.5px solid #eee;font-size:12px">[{rule['id']}] {rule['name']}</td>
  <td style="padding:8px;border-bottom:0.5px solid #eee;font-size:12px;color:#555">{rule['regulation']}</td>
</tr>'''

    return alert_html


def _build_guarantee_note(industry: str, fin: Dict) -> str:
    """构建担保行业专项说明"""
    if industry != '担保/金融服务':
        return ''

    deposit_out = fin.get('deposit_out', 0) or 0
    paid_capital = fin.get('paid_in_capital', 0) or 0
    total_assets_v = fin.get('total_assets', 0) or 0

    return f'''
<div class="card" style="border-left:4px solid #4F46E5">
  <h2>🏛️ 担保公司专项监管指标</h2>
  <div style="display:flex;flex-wrap:wrap;gap:20px;margin-top:8px">
    <div>
      <div style="font-size:12px;color:#888">存出保证金</div>
      <div style="font-size:16px;font-weight:500">{_fmt(deposit_out, '元')}</div>
      <div style="font-size:11px;color:#888;margin-top:2px">在保业务担保金</div>
    </div>
    <div>
      <div style="font-size:12px;color:#888">实收资本</div>
      <div style="font-size:16px;font-weight:500">{_fmt(paid_capital, '元')}</div>
      <div style="font-size:11px;color:#888;margin-top:2px">注册资本</div>
    </div>
    <div>
      <div style="font-size:12px;color:#888">保证金/注册资本比</div>
      <div style="font-size:16px;font-weight:500">{_fmt(deposit_out/paid_capital if paid_capital else None)}</div>
      <div style="font-size:11px;color:#888;margin-top:2px">参考监管上限 10 倍</div>
    </div>
    <div>
      <div style="font-size:12px;color:#888">净资本充足率</div>
      <div style="font-size:16px;font-weight:500">{_fmt(paid_capital/total_assets_v if total_assets_v else None, '%', pct=True)}</div>
      <div style="font-size:11px;color:#888;margin-top:2px">建议 ≥ 40%</div>
    </div>
  </div>
</div>'''


def _build_financial_tables(three_stmt: Optional[Dict], fin: Dict) -> Tuple[str, str, str]:
    """构建三表HTML"""
    if not three_stmt:
        return '', '', ''

    balance_sheet_html = ''
    if three_stmt.get('balance_sheet'):
        balance_sheet_html = f'''
<div class="card">
  <h2>📊 资产负债表</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:8px">
    {_build_balance_sheet_table(fin)}
  </div>
</div>'''

    # 利润表 + 现金流量表并排
    income_stmt_html = ''
    cash_flow_html = ''
    inc_table = _build_income_statement_table(fin) if three_stmt.get('income_statement') else ''
    cf_table = _build_cash_flow_table(fin) if three_stmt.get('cash_flow') else ''

    if inc_table or cf_table:
        side_by_side = ''
        if inc_table:
            side_by_side += f'''
    <div style="flex:1;min-width:0">
      <h3 style="font-size:13px;font-weight:600;color:#333;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb">📈 利润表</h3>
      <table style="width:100%;border-collapse:collapse">
        <tbody>{inc_table}</tbody>
      </table>
    </div>'''
        if cf_table:
            side_by_side += f'''
    <div style="flex:1;min-width:0">
      <h3 style="font-size:13px;font-weight:600;color:#333;margin-bottom:8px;padding-bottom:6px;border-bottom:1px solid #e5e7eb">💵 现金流量表</h3>
      <table style="width:100%;border-collapse:collapse">
        <tbody>{cf_table}</tbody>
      </table>
    </div>'''

        income_stmt_html = f'''
<div class="card">
  <h2>📈💵 利润表 & 现金流量表</h2>
  <div style="display:flex;gap:24px;margin-top:8px">{side_by_side}
  </div>
</div>'''
        cash_flow_html = ''  # 已合并，不再单独输出

    return balance_sheet_html, income_stmt_html, cash_flow_html


def generate_report(
    company_name: str,
    industry: str,
    metrics: Dict,
    score_result: Dict,
    fin: Dict,
    fin_prev: Optional[Dict],
    tax: Dict,
    file_list: List[str],
    periods: List[str],
    period_details: Dict,
    output_path: str,
    analysis_notes: Optional[List[str]] = None,
    period_info: Optional[Dict] = None,
    three_stmt: Optional[Dict] = None,
    consistency_result: Optional[List[Dict]] = None,
):
    """
    生成授信决策报告 v3.0
    """
    now = datetime.now().strftime('%Y年%m月%d日 %H:%M')
    grade = score_result['grade']
    total_score = score_result['total_score']
    suggestion = score_result['suggestion']
    g_color = GRADE_COLOR.get(score_result['color'], GRADE_COLOR['yellow'])
    dim_scores = score_result['dimension_scores']
    weights = score_result['weights']

    dim_labels = {
        'solvency': '偿债能力', 'profitability': '盈利能力',
        'cashflow': '现金流质量', 'operations': '营运能力',
        'tax_compliance': '税务合规', 'fraud_alert': '造假预警',
    }

    # 雷达图数据
    radar_labels = [dim_labels.get(d, d) for d in dim_scores]
    radar_values = [dim_scores[d] for d in dim_scores]
    radar_js = json.dumps({'labels': radar_labels, 'values': radar_values})

    # 跨期对比图数据
    compare_chart_js = _build_compare_chart_data(periods, period_details)

    # 构建各组件
    period_badges, period_type_info = _build_period_type_info(periods, period_details)
    cross_period_notes = _build_analysis_notes_html(analysis_notes)
    sections = _build_sections(metrics, dim_labels)
    trend_section = _build_trend_section(metrics, periods, period_details)
    kpi_cards = _build_kpi_cards(fin, metrics, fin_prev, periods)
    alert_html = _build_alert_table(metrics)

    # 授信额度估算
    total_equity_v = fin.get('total_equity', 0) or 0
    total_assets_v = fin.get('total_assets', 0) or 0
    revenue_v = fin.get('revenue', 0) or 0
    latest_period = periods[-1] if periods else ''
    annual_rev = revenue_v * 4 if latest_period.endswith('-03') else revenue_v
    credit_estimate = _build_credit_estimate(total_score, total_assets_v, annual_rev, total_equity_v)

    # 担保行业专项
    guarantee_note = _build_guarantee_note(industry, fin)

    # v3.0 新增模块
    file_list_html = _build_file_list_html(file_list, three_stmt or {})
    consistency_html = _build_consistency_check_html(three_stmt or {}, consistency_result or [])
    mscore_html = _build_mscore_detail_html(metrics)
    knowledge_base_html = _build_knowledge_base_section(metrics)
    balance_sheet_html, income_stmt_html, cash_flow_html = _build_financial_tables(three_stmt, fin)
    benchmark_html = _build_industry_benchmark(industry)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>信贷风险分析报告 v3.0 - {company_name}</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js"></script>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Helvetica Neue",sans-serif;
  background:#f4f5f7;color:#222;font-size:14px;line-height:1.6}}
.container{{max-width:1200px;margin:0 auto;padding:24px 16px}}
.card{{background:#fff;border-radius:12px;border:0.5px solid #e5e7eb;padding:24px;margin-bottom:20px}}
h1{{font-size:20px;font-weight:600;color:#111;margin-bottom:4px}}
h2{{font-size:15px;font-weight:500;color:#222;margin-bottom:14px;padding-bottom:8px;
  border-bottom:1px solid #f0f0f0}}
h3{{font-size:13px;font-weight:500;color:#444;margin:12px 0 6px}}
table{{width:100%;border-collapse:collapse}}
th{{font-size:12px;font-weight:500;color:#666;padding:8px;background:#f8f9fa;
  border-bottom:1px solid #e5e7eb;text-align:left}}
.version-badge{{background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:2px 10px;border-radius:10px;font-size:11px;font-weight:500;margin-left:8px}}
@media print{{body{{background:#fff}}.card{{border:1px solid #ddd}}}}
</style>
</head>
<body>
<div class="container">

<!-- ══ 封面 + 核心指标（双栏表格布局）══ -->
<div class="card" style="padding:0;overflow:hidden">
  <!-- 顶部标题栏 -->
  <div style="background:linear-gradient(135deg,#1e293b,#334155);color:#fff;padding:16px 24px;
       display:flex;justify-content:space-between;align-items:center">
    <div>
      <div style="font-size:12px;opacity:0.7;margin-bottom:2px">银行信贷风险部 · 授信决策报告 <span style="background:rgba(255,255,255,0.15);padding:2px 8px;border-radius:8px;font-size:10px">v3.0</span></div>
      <div style="font-size:18px;font-weight:600">📊 {company_name}</div>
      <div style="font-size:13px;opacity:0.8;margin-top:4px">
        {industry} &nbsp;·&nbsp; {now} &nbsp;·&nbsp; {period_badges}
      </div>
    </div>
    <div style="text-align:center">
      <div style="font-size:42px;font-weight:700;color:{g_color[2]};line-height:1.1">{grade}</div>
      <div style="font-size:22px;font-weight:600;margin-top:2px">{total_score:.1f}<span style="font-size:12px;opacity:0.7">分</span></div>
    </div>
  </div>

  <!-- 授信建议条 -->
  <div style="padding:10px 24px;background:{g_color[1]};border-bottom:1px solid #e5e7eb">
    <b style="color:{g_color[0]};font-size:13px">💡 授信建议：</b>
    <span style="color:{g_color[0]};font-size:13px">{suggestion}</span>
    <span style="margin-left:16px;font-size:12px;color:#555">{credit_estimate}</span>
  </div>

  <!-- 双栏表格区 -->
  <div style="display:grid;grid-template-columns:1fr 1fr;border-top:1px solid #e5e7eb">
    <!-- 左栏：企业信息 + 期间识别 -->
    <div style="padding:16px 24px;border-right:1px solid #e5e7eb">
      <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:10px">📋 企业信息</div>
      <table style="width:100%;font-size:12px">
        <tr><td style="color:#888;padding:4px 0;width:80px">企业名称</td><td style="font-weight:500;padding:4px 0">{company_name}</td></tr>
        <tr><td style="color:#888;padding:4px 0">行业分类</td><td style="font-weight:500;padding:4px 0">{industry}</td></tr>
        <tr><td style="color:#888;padding:4px 0">分析期间</td><td style="padding:4px 0">{'、'.join(periods) if periods else '—'}</td></tr>
        <tr><td style="color:#888;padding:4px 0">报告类型</td><td style="padding:4px 0">{period_type_info}</td></tr>
      </table>
    </div>

    <!-- 右栏：核心财务指标 -->
    <div style="padding:16px 24px">
      <div style="font-size:13px;font-weight:600;color:#374151;margin-bottom:10px">
        📌 核心指标 {f'<span style="font-size:11px;color:#888;font-weight:400">（{latest_period}）</span>' if latest_period else ''}
      </div>
      <table style="width:100%;font-size:12px">
        {kpi_cards}
      </table>
    </div>
  </div>
</div>

<!-- ══ 分析说明 ══ -->
{cross_period_notes}

<!-- ══ 担保专项 ══ -->
{guarantee_note}

<!-- ══ 增强版输入文件清单 ══ -->
{file_list_html}

<!-- ══ 六维评分雷达 ══ -->
<div class="card">
  <h2>🎯 六维综合评分</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:24px">
    <div style="position:relative;height:300px">
      <canvas id="radarChart" role="img" aria-label="六维风险雷达图"></canvas>
    </div>
    <div>
      {''.join(
          f'''<div style="margin-bottom:16px">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px">
              <span style="font-size:13px">{dim_labels.get(d,d)}</span>
              <span style="font-size:12px;color:#888">权重 {int(weights.get(d,0)*100)}%</span>
            </div>
            {_score_bar(dim_scores.get(d,0), 160)}
          </div>'''
          for d in dim_scores
      )}
    </div>
  </div>
</div>

<!-- ══ v3.0 新增模块 ══ -->
{consistency_html}
{mscore_html}

<!-- ══ 跨期对比图 ══ -->
{_build_compare_chart_html(periods, period_details, compare_chart_js) if len(periods) > 1 else ''}

<!-- 财务报表三表展示 -->
{balance_sheet_html}
{income_stmt_html}
{cash_flow_html}

<!-- 行业基准对照 -->
{benchmark_html}

<!-- ══ 风险预警清单（知识库触发汇总） ══ -->
<div class="card">
  <h2>⚠️ 风险预警清单（知识库触发汇总）</h2>
  <table>
    <thead><tr>
      <th>指标</th><th>风险等级</th><th>触发规则</th><th>监管依据</th>
    </tr></thead>
    <tbody>{alert_html}</tbody>
  </table>
</div>

<!-- ══ 六维度详细分析 ══ -->
{sections}

<!-- ══ 跨期趋势分析 ══ -->
{trend_section}

<!-- ══ 知识库评判结果 ══ -->
{knowledge_base_html}

<!-- ══ 信用评级说明（三级九等） ══ -->
<div class="card">
  <h2>🏆 信用评级说明</h2>
  <p style="font-size:12px;color:#666;margin-bottom:12px">
    本报告采用银行通用「三级九等」信用评级体系，综合评分由六维风险评估模型计算得出。
  </p>
  <table style="font-size:12px">
    <thead>
      <tr>
        <th style="width:14%;padding:8px;text-align:center">信用等级</th>
        <th style="width:18%;padding:8px;text-align:center">评分区间</th>
        <th style="width:20%;padding:8px;text-align:center">授信建议</th>
        <th style="width:48%;padding:8px">评级说明</th>
      </tr>
    </thead>
    <tbody>
      <tr style="background:#eaf3de">
        <td style="padding:8px;text-align:center;font-weight:600;color:#1a6b3a">AAA</td>
        <td style="padding:8px;text-align:center">90-100分</td>
        <td style="padding:8px;text-align:center;color:#1a6b3a;font-weight:500">建议足额授信</td>
        <td style="padding:8px;color:#555">偿债能力极强，各项财务指标优良，经营稳健，风险极低</td>
      </tr>
      <tr style="background:#f0f7ec">
        <td style="padding:8px;text-align:center;font-weight:600;color:#1a6b3a">AA</td>
        <td style="padding:8px;text-align:center">80-89分</td>
        <td style="padding:8px;text-align:center;color:#1a6b3a;font-weight:500">建议正常授信</td>
        <td style="padding:8px;color:#555">偿债能力强，财务状况良好，具有较强的抗风险能力</td>
      </tr>
      <tr style="background:#f9fcf5">
        <td style="padding:8px;text-align:center;font-weight:600;color:#2d7a45">A</td>
        <td style="padding:8px;text-align:center">70-79分</td>
        <td style="padding:8px;text-align:center;color:#7a5c00;font-weight:500">审慎授信</td>
        <td style="padding:8px;color:#555">偿债能力良好，部分指标需关注，整体风险可控</td>
      </tr>
      <tr style="background:#fef9e7">
        <td style="padding:8px;text-align:center;font-weight:600;color:#7a5c00">BBB</td>
        <td style="padding:8px;text-align:center">60-69分</td>
        <td style="padding:8px;text-align:center;color:#7a5c00;font-weight:500">附条件授信</td>
        <td style="padding:8px;color:#555">偿债能力一般，需附加担保或抵押条件，建议压缩授信期限</td>
      </tr>
      <tr style="background:#fff5ee">
        <td style="padding:8px;text-align:center;font-weight:600;color:#854f0b">BB</td>
        <td style="padding:8px;text-align:center">50-59分</td>
        <td style="padding:8px;text-align:center;color:#854f0b;font-weight:500">压缩授信额度</td>
        <td style="padding:8px;color:#555">偿债能力偏弱，存在一定风险，建议大幅压缩额度</td>
      </tr>
      <tr style="background:#fde8e8">
        <td style="padding:8px;text-align:center;font-weight:600;color:#7a1010">B</td>
        <td style="padding:8px;text-align:center">40-49分</td>
        <td style="padding:8px;text-align:center;color:#7a1010;font-weight:500">建议拒绝或强担保</td>
        <td style="padding:8px;color:#555">偿债能力不足，风险较高，需提供强担保措施方可考虑</td>
      </tr>
      <tr style="background:#fddddd">
        <td style="padding:8px;text-align:center;font-weight:600;color:#7a1010">CCC</td>
        <td style="padding:8px;text-align:center">0-39分</td>
        <td style="padding:8px;text-align:center;color:#7a1010;font-weight:500">建议拒绝授信</td>
        <td style="padding:8px;color:#555">偿债能力严重不足，财务状况堪忧，建议拒绝授信</td>
      </tr>
    </tbody>
  </table>
  <div style="margin-top:12px;padding:10px 14px;background:#f8f9fa;border-radius:6px;font-size:12px;color:#666">
    <b>评级维度说明：</b>综合评分基于偿债能力（35%）、盈利能力（20%）、现金流质量（15%）、
    营运能力（10%）、税务合规（15%）、造假预警（5%）六维度计算，各行业权重有所不同。
  </div>
</div>

<!-- ══ 结尾声明 ══ -->
<div class="card" style="font-size:12px;color:#999;text-align:center">
  本报告由信贷风险分析系统 v3.0 自动生成，仅供决策参考，不构成最终授信决定。<br>
  最终授信决策须经信贷委员会审批，并符合相关监管要求。<br>
  报告生成时间：{now}
</div>

</div>

<script>
// 雷达图
const radarData = {radar_js};
new Chart(document.getElementById('radarChart'), {{
  type: 'radar',
  data: {{
    labels: radarData.labels,
    datasets: [{{
      label: '综合评分',
      data: radarData.values,
      borderColor: '#4F46E5',
      backgroundColor: 'rgba(79,70,229,0.12)',
      borderWidth: 2,
      pointBackgroundColor: '#4F46E5',
      pointRadius: 4,
    }}]
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ display: false }} }},
    scales: {{ r: {{
      min: 0, max: 100,
      ticks: {{ stepSize: 20, font: {{ size: 11 }} }},
      pointLabels: {{ font: {{ size: 12 }} }},
      grid: {{ color: 'rgba(0,0,0,0.08)' }},
    }} }}
  }}
}});

{_build_compare_chart_script(periods, compare_chart_js) if len(periods) > 1 else ''}
</script>
</body></html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path


# ─────────────────────────────────────────────
# 跨期对比图构建
# ─────────────────────────────────────────────

def _build_compare_chart_data(periods: List[str], period_details: Dict) -> Dict:
    """构建跨期对比数据"""
    key_items = [
        ('total_assets',    '总资产'),
        ('total_equity',    '所有者权益'),
        ('total_liabilities', '总负债'),
        ('revenue',         '营业收入'),
        ('cost_of_sales',   '业务成本'),
        ('net_profit',      '净利润'),
        ('current_assets',  '流动资产'),
        ('current_liabilities', '流动负债'),
    ]
    datasets = []
    for key, label in key_items:
        vals = []
        for p in periods:
            fin = period_details.get(p, {}).get('financial', {})
            v = fin.get(key)
            vals.append(round(v / 1e4, 2) if v is not None else None)
        datasets.append({'label': label, 'values': vals})

    return {'periods': periods, 'datasets': datasets}


def _build_compare_chart_html(periods, period_details, chart_data_js) -> str:
    if len(periods) < 2:
        return ''
    return f'''
<div class="card">
  <h2>📈 跨期财务对比分析
    <span style="font-size:12px;color:#888;font-weight:400">（单位：万元）</span>
  </h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px">
    <div>
      <h3>资产负债对比</h3>
      <div style="position:relative;height:260px">
        <canvas id="balanceCompareChart"></canvas>
      </div>
    </div>
    <div>
      <h3>收益对比</h3>
      <div style="position:relative;height:260px">
        <canvas id="incomeCompareChart"></canvas>
      </div>
    </div>
  </div>
  {_build_period_comparison_table(periods, period_details)}
</div>'''


def _build_period_comparison_table(periods: List[str], period_details: Dict) -> str:
    """构建跨期数据对比表"""
    key_items = [
        ('total_assets',      '资产总额'),
        ('current_assets',    '流动资产'),
        ('deposit_out',       '存出保证金'),
        ('total_liabilities', '总负债'),
        ('current_liabilities', '流动负债'),
        ('total_equity',      '所有者权益'),
        ('retained_earnings', '未分配利润'),
        ('revenue',           '担保业务收入'),
        ('cost_of_sales',     '担保业务成本'),
        ('net_profit',        '净利润'),
    ]

    header = '<tr><th style="padding:8px;text-align:left">科目</th>'
    for p in periods:
        header += f'<th style="padding:8px;text-align:right">{p}</th>'
    if len(periods) == 2:
        header += '<th style="padding:8px;text-align:right">变动额（万元）</th><th style="padding:8px;text-align:right">变动率</th>'
    header += '</tr>'

    rows = ''
    for key, label in key_items:
        vals = []
        for p in periods:
            fin = period_details.get(p, {}).get('financial', {})
            vals.append(fin.get(key))

        row = f'<tr><td style="padding:7px 8px;font-size:12px;font-weight:500">{label}</td>'
        for v in vals:
            vstr = f'{v/1e4:,.2f}' if v is not None else 'N/A'
            row += f'<td style="padding:7px 8px;font-size:12px;text-align:right">{vstr}</td>'

        if len(vals) == 2:
            if vals[0] is not None and vals[1] is not None:
                delta = vals[1] - vals[0]
                pct = (delta / abs(vals[0]) * 100) if abs(vals[0]) > 1 else 0
                color = '#1D9E75' if delta >= 0 else '#D85A30'
                row += f'<td style="padding:7px 8px;font-size:12px;text-align:right;color:{color}">{delta/1e4:+,.2f}</td>'
                row += f'<td style="padding:7px 8px;font-size:12px;text-align:right;color:{color}">{pct:+.1f}%</td>'
            else:
                row += '<td style="padding:7px 8px;font-size:12px;text-align:right;color:#888">N/A</td>'
                row += '<td style="padding:7px 8px;font-size:12px;text-align:right;color:#888">N/A</td>'

        row += '</tr>'
        rows += row

    return f'''
<div style="margin-top:20px">
  <h3>各期关键科目对比（万元）</h3>
  <table style="margin-top:8px;table-layout:fixed">
    <thead style="background:#f8f9fa">{header}</thead>
    <tbody>{rows}</tbody>
  </table>
</div>'''


def _build_compare_chart_script(periods: List[str], chart_data) -> str:
    if not chart_data or len(periods) < 2:
        return ''

    COLORS = [
        'rgba(79,70,229,0.8)', 'rgba(16,185,129,0.8)', 'rgba(245,158,11,0.8)',
        'rgba(239,68,68,0.8)', 'rgba(99,102,241,0.8)', 'rgba(52,211,153,0.8)',
    ]

    balance_keys = ['总资产', '所有者权益', '总负债', '流动资产', '流动负债']
    income_keys = ['营业收入', '业务成本', '净利润']

    def make_datasets(keys_filter, colors_offset=0):
        ds = []
        for i, item in enumerate(chart_data.get('datasets', [])):
            if item['label'] not in keys_filter:
                continue
            ds.append({
                'label': item['label'],
                'data': item['values'],
                'backgroundColor': COLORS[(i + colors_offset) % len(COLORS)],
                'borderRadius': 4,
            })
        return json.dumps(ds)

    balance_ds = make_datasets(balance_keys)
    income_ds = make_datasets(income_keys, colors_offset=3)
    periods_json = json.dumps(periods)

    return f'''
// 资产负债对比图
new Chart(document.getElementById('balanceCompareChart'), {{
  type: 'bar',
  data: {{
    labels: {periods_json},
    datasets: {balance_ds}
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{ y: {{ title: {{ display: true, text: '万元', font: {{ size: 11 }} }} }} }}
  }}
}});

// 收益对比图
new Chart(document.getElementById('incomeCompareChart'), {{
  type: 'bar',
  data: {{
    labels: {periods_json},
    datasets: {income_ds}
  }},
  options: {{
    responsive: true, maintainAspectRatio: false,
    plugins: {{ legend: {{ position: 'bottom', labels: {{ font: {{ size: 11 }} }} }} }},
    scales: {{ y: {{ title: {{ display: true, text: '万元', font: {{ size: 11 }} }} }} }}
  }}
}});
'''


# ─────────────────────────────────────────────
# 六维度详细分析块
# ─────────────────────────────────────────────

def _build_sections(metrics: Dict, dim_labels: Dict) -> str:
    from risk_analyzer import DIMENSION_METRIC_MAP

    dim_order = ['solvency', 'profitability', 'cashflow', 'operations', 'tax_compliance', 'fraud_alert']
    dim_icons = {
        'solvency': '🏦', 'profitability': '📈', 'cashflow': '💵',
        'operations': '⚙️', 'tax_compliance': '📋', 'fraud_alert': '🔍'
    }

    html = ''
    for dim in dim_order:
        keys = DIMENSION_METRIC_MAP.get(dim, [])
        label = dim_labels.get(dim, dim)
        icon = dim_icons.get(dim, '')

        rows = ''
        for key in keys:
            if key not in metrics:
                continue
            m = metrics[key]
            if m.get('trend_type'):  # 跨期趋势指标放到趋势分析块
                continue
            v = m.get('value')
            unit = m.get('unit', '')
            score = m.get('score', 0) or 0
            rules = m.get('triggered_rules', [])
            is_pct = unit == '%'
            display_val = _fmt(v, unit, pct=is_pct)
            rule_html = ''.join(_rule_tag(r) for r in rules) if rules else ''

            rows += f'''
<tr>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0;font-size:13px;font-weight:500">
    {m["label"]}</td>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0;font-size:13px">
    {display_val}</td>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0;font-size:12px;color:#888">
    {m.get("benchmark","")}</td>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0">
    {_score_bar(score, 100)}</td>
</tr>'''
            if rule_html:
                rows += f'<tr><td colspan="4" style="padding:4px 8px 12px;background:#fafafa">{rule_html}</td></tr>'

        if not rows:
            continue

        html += f'''
<div class="card">
  <h2>{icon} {label}分析</h2>
  <table>
    <thead><tr>
      <th style="width:26%">指标名称</th>
      <th style="width:18%">计算值</th>
      <th style="width:30%">参考基准</th>
      <th style="width:26%">得分</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>'''

    return html


# ─────────────────────────────────────────────
# 跨期趋势分析块
# ─────────────────────────────────────────────

def _build_trend_section(metrics: Dict, periods: List[str], period_details: Dict = None) -> str:
    trend_metrics = {k: v for k, v in metrics.items() if v.get('trend_type')}
    if not trend_metrics:
        return ''

    period_label = f'{periods[0]} → {periods[-1]}' if len(periods) >= 2 else ''
    rows = ''
    for key, m in trend_metrics.items():
        v = m.get('value')
        unit = m.get('unit', '')
        score = m.get('score', 0) or 0
        is_pct = unit == '%'
        display_val = _fmt(v, unit, pct=is_pct)
        rules = m.get('triggered_rules', [])
        rule_html = ''.join(_rule_tag(r) for r in rules) if rules else ''

        if v is not None:
            if v > 0.01:
                arrow = f'<span style="color:#1D9E75">▲</span>'
            elif v < -0.01:
                arrow = f'<span style="color:#D85A30">▼</span>'
            else:
                arrow = f'<span style="color:#888">─</span>'
        else:
            arrow = ''

        rows += f'''
<tr>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0;font-size:13px;font-weight:500">
    {arrow} {m["label"]}</td>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0;font-size:13px">
    {display_val}</td>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0;font-size:12px;color:#888">
    {m.get("benchmark","")}</td>
  <td style="padding:10px 8px;border-bottom:0.5px solid #f0f0f0">
    {_score_bar(score, 100)}</td>
</tr>'''
        if rule_html:
            rows += f'<tr><td colspan="4" style="padding:4px 8px 12px;background:#fafafa">{rule_html}</td></tr>'

    if not rows:
        return ''

    # 动态生成趋势说明（基于实际期间信息，不再硬编码年份）
    trend_note = '趋势指标基于两期实际数据计算，仅供参考'
    if period_details and len(periods) >= 2:
        note_parts = []
        new_pi = (period_details.get(periods[-1], {}) or {}).get('period_info', {})
        old_pi = (period_details.get(periods[0], {}) or {}).get('period_info', {})
        new_type = new_pi.get('report_type', '')
        old_type = old_pi.get('report_type', '')
        new_factor = new_pi.get('annualization_factor', 1.0)
        if new_factor > 1.0 and new_type == 'quarterly':
            q_num = int(12 / new_factor)
            note_parts.append(f'最新期（Q{q_num}）收入/利润数据已按 ×{new_factor:.1f} 年化折算')
        if old_type == 'annual' and new_type == 'quarterly':
            note_parts.append(f'与上期（{periods[0]}，年度）跨期对比')
        if note_parts:
            trend_note = '；'.join(note_parts) + '，仅供参考'

    return f'''
<div class="card">
  <h2>📊 跨期趋势分析
    {f'<span style="font-size:12px;color:#888;font-weight:400">（{period_label}）</span>' if period_label else ''}
  </h2>
  <p style="font-size:12px;color:#888;margin-bottom:12px">
    注：{trend_note}
  </p>
  <table>
    <thead><tr>
      <th style="width:30%">趋势指标</th>
      <th style="width:20%">变化值</th>
      <th style="width:28%">参考基准</th>
      <th style="width:22%">得分</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
</div>'''


# ─────────────────────────────────────────────
# 授信额度估算
# ─────────────────────────────────────────────

def _build_credit_estimate(total_score: float, total_assets: float,
                            annual_rev: float, total_equity: float) -> str:
    if total_score >= 70 and total_assets > 0:
        base = min(
            total_assets * 0.30,
            annual_rev * 0.5 if annual_rev else float('inf'),
            total_equity * 0.5 if total_equity else float('inf'),
        )
        base_str = _fmt(base, '元')
        return (f'基于综合评分 {total_score:.0f} 分，建议授信额度参考区间：<b>{base_str}</b>。'
                f'（测算依据：总资产×30%、年化收入×50%、净资产×50%取最小值；'
                f'最终额度须结合担保业务规模、在保余额及监管杠杆限制综合确定）')
    elif total_score >= 50:
        return '评分偏低，建议附加担保条件后再确定授信额度，或将授信期限压缩至12个月以内'
    else:
        return '综合评分不足，建议拒绝授信，或要求提供强担保措施后重新评估'
