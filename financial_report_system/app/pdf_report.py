# -*- coding: utf-8 -*-
"""
专业 PDF 报告生成器 v2
优化：表格列间距、字体层次、颜色对比、分页控制、内容换行
使用 STSong-Light CID 字体，无 emoji，无 canvas
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
import os


def generate_pdf_report(
    company_name: str,
    industry: str,
    analysis_result: Dict,
    output_path: str,
) -> str:
    now = datetime.now().strftime('%Y 年 %m 月 %d 日')
    metrics = analysis_result.get('metrics', {})
    period_details = analysis_result.get('period_details', {})
    periods = analysis_result.get('periods', [])
    three_stmt = analysis_result.get('three_stmt', {})
    fin = analysis_result.get('financial', {})
    consistency_result = analysis_result.get('consistency_result', [])

    total_score = analysis_result.get('total_score', 0) or 0
    grade = analysis_result.get('grade', 'N/A')
    suggestion = analysis_result.get('suggestion', '')
    color = analysis_result.get('color', 'yellow')
    dim_scores = analysis_result.get('dimension_scores', {})
    weights = analysis_result.get('weights', {})
    veto = analysis_result.get('veto', False)
    file_list = analysis_result.get('file_list', [])

    dim_labels = {
        'solvency': '偿债能力', 'profitability': '盈利能力',
        'cashflow': '现金流质量', 'operations': '营运能力',
        'tax_compliance': '税务合规', 'fraud_alert': '造假预警',
    }

    grade_color_map = {
        'green': ('#1D7A4C', '#E8F5E9'),
        'yellow': ('#7A5C00', '#FFF8E1'),
        'orange': ('#854F0B', '#FFF3E0'),
        'red': ('#A32D2D', '#FFEBEE'),
    }
    gc = grade_color_map.get(color, grade_color_map['yellow'])

    # ── Build sections ──
    cover = _build_cover(company_name, industry, now, grade, total_score, suggestion, gc, veto)
    info = _build_company_info(company_name, industry, periods, period_details, file_list, now)
    kpi = _build_kpi_table(fin, metrics, periods)
    dim_section = _build_dimension_scores(dim_scores, weights, dim_labels, total_score, grade, gc)
    mscore_section = _build_mscore_section(metrics)
    consistency = _build_consistency_check(consistency_result)
    fin_tables = _build_financial_tables(three_stmt, fin)
    kb_section = _build_knowledge_base_section(metrics)
    rating = _build_credit_rating_table()

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8"/>
<style>
@page {{ size:A4; margin:2cm 1.8cm 2cm 1.8cm }}
body {{ font-family:STSong-Light,HeiseiMin-W3,HeiseiKakuGo-W5,MSung-Light,sans-serif; font-size:11pt; color:#111; line-height:1.7; word-wrap:break-word; overflow-wrap:break-word; font-weight:500 }}
h1 {{ font-size:17pt; margin:0 0 6pt 0; font-weight:bold; color:#0A1A2E; letter-spacing:0.5pt }}
h2 {{ font-size:14pt; margin:20pt 0 10pt 0; padding-bottom:6pt; border-bottom:2pt solid #0A1A2E; color:#0A1A2E; font-weight:bold; page-break-after:avoid }}
h3 {{ font-size:12pt; margin:12pt 0 6pt 0; color:#222; font-weight:bold; page-break-after:avoid }}
table {{ width:100%; border-collapse:collapse; margin:8pt 0; font-size:11pt; page-break-inside:auto }}
tr {{ page-break-inside:avoid; page-break-after:auto }}
th {{ background:#0A1A2E; color:#fff; padding:6pt 8pt; text-align:left; font-weight:bold; font-size:10pt; letter-spacing:0.3pt }}
td {{ padding:5pt 8pt; border-bottom:0.5pt solid #B0B4B8; font-size:11pt; color:#111; vertical-align:top; word-wrap:break-word; overflow-wrap:break-word; font-weight:500 }}
tr:nth-child(even) td {{ background:#F0F2F5 }}
.total-row td {{ font-weight:bold; background:#DCE0E5; border-top:1.5pt solid #909498; color:#000 }}
.cover-page {{ text-align:center; padding-top:100pt; page-break-after:always }}
.cover-rule {{ width:60pt; height:2.5pt; background:#0A1A2E; margin:16pt auto }}
.cover-title {{ font-size:24pt; font-weight:bold; color:#0A1A2E; letter-spacing:1pt; margin:20pt 0 8pt 0 }}
.cover-sub {{ font-size:15pt; color:#222; font-weight:600; margin:8pt 0 }}
.cover-meta {{ font-size:11pt; color:#444; font-weight:500; margin:4pt 0 }}
.grade-display {{ display:inline-block; padding:12pt 30pt; border-radius:3pt; font-size:34pt; font-weight:bold; text-align:center; margin:16pt 0; border:2pt solid }}
.score-text {{ font-size:17pt; font-weight:bold; margin:6pt 0 }}
.suggestion-box {{ padding:10pt 14pt; border-left:4pt solid #0A1A2E; margin:12pt auto; font-size:11pt; max-width:420pt; text-align:left; font-weight:500 }}
.badge {{ display:inline-block; padding:2pt 8pt; border-radius:3pt; font-size:9pt; font-weight:bold; letter-spacing:0.3pt }}
.badge-annual {{ background:#E3F2FD; color:#1565C0 }}
.badge-quarterly {{ background:#FFF3E0; color:#E65100 }}
.sec {{ margin:0 0 16pt 0 }}
.label-col {{ color:#333; width:110pt; white-space:nowrap; font-weight:600 }}
.val-col {{ font-weight:bold; word-wrap:break-word; color:#000 }}
.score-bg {{ background:#D0D4D8; height:12pt; border-radius:2pt; overflow:hidden }}
.score-fill {{ height:100%; border-radius:2pt }}
.page-break {{ page-break-before:always }}
.footer {{ margin-top:24pt; font-size:8pt; color:#999; text-align:center; border-top:0.5pt solid #B0B4B8; padding-top:10pt }}
</style>
</head>
<body>

<div class="cover-page">{cover}</div>

<div class="sec">{info}</div>
<div class="sec">{kpi}</div>
<div class="sec">{dim_section}</div>
<div class="sec">{mscore_section}</div>
<div class="sec page-break">{consistency}</div>
<div class="sec">{fin_tables}</div>
<div class="sec page-break">{kb_section}</div>
<div class="sec">{rating}</div>

<div class="footer">
本报告由信贷风险分析系统 v3.0 自动生成，仅供决策参考，不构成最终授信决定。<br/>
报告生成时间：{now}
</div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    return output_path


# ═══════════════════════════════════════════════════
# Cover
# ═══════════════════════════════════════════════════
def _build_cover(company_name, industry, now, grade, total_score, suggestion, gc, veto):
    gcolor, gbg = gc
    return f'''
<div style="margin-top:60pt">
  <div style="font-size:10pt;color:#888;letter-spacing:2pt;margin-bottom:4pt">银 行 信 贷 风 险 部</div>
  <div class="cover-rule"></div>
  <div class="cover-title">企业信用风险分析报告</div>
  <div class="cover-rule"></div>
  <div class="cover-sub">{company_name}</div>
  <div class="cover-meta">行业分类：{industry}</div>
  <div class="cover-meta">报告日期：{now}</div>
  <div class="grade-display" style="background:{gbg};color:{gcolor};border-color:{gcolor}">{grade}</div>
  <div class="score-text" style="color:{gcolor}">综合评分：{total_score:.1f} 分</div>
  <div class="suggestion-box" style="background:{gbg}">
    <b style="color:{gcolor}">授信建议：</b>
    <span style="color:{gcolor}">{suggestion}</span>
    {'<br/><span style="color:#A32D2D;font-weight:bold">（一票否决：M-Score 财务造假预警触发）</span>' if veto else ''}
  </div>
</div>'''


# ═══════════════════════════════════════════════════
# Company Info
# ═══════════════════════════════════════════════════
def _build_company_info(company_name, industry, periods, period_details, file_list, now):
    period_info = ''
    for p in periods:
        d = period_details.get(p, {})
        pi = d.get('period_info', {})
        rtype = pi.get('report_type', 'unknown')
        conf = pi.get('confidence', 0)
        factor = pi.get('annualization_factor', 1.0)
        rtype_map = {'annual': ('年报', 'badge-annual'), 'quarterly': ('季报', 'badge-quarterly'), 'monthly': ('月报', '')}
        rt_label, rt_class = rtype_map.get(rtype, ('未知', ''))
        note = f'<span class="badge {rt_class}">{rt_label}</span> 置信度 {conf:.0%}'
        if factor != 1.0:
            note += f' <span style="color:#1565C0;font-size:8.5pt">{factor:.1f}x 年化</span>'
        period_info += f'<tr><td style="font-weight:bold;color:#333;width:110pt">{p}</td><td style="font-weight:600">{note}</td></tr>'

    files_html = ''
    for f in file_list:
        files_html += f'<div style="font-size:9pt;color:#666;padding:1pt 0">{os.path.basename(f)}</div>'

    return f'''
<h2>一、企业基本信息</h2>
<table>
  <tr><td class="label-col" style="font-weight:bold">企业名称</td><td class="val-col" style="font-weight:bold;font-size:12pt">{company_name}</td></tr>
  <tr><td class="label-col" style="font-weight:bold">行业分类</td><td style="font-weight:600">{industry}</td></tr>
  <tr><td class="label-col" style="font-weight:bold">分析期间</td><td style="font-weight:600">{'、'.join(periods) if periods else '—'}</td></tr>
  {period_info}
  <tr><td class="label-col" style="font-weight:bold">分析日期</td><td>{now}</td></tr>
  <tr><td class="label-col" style="font-weight:bold">输入文件</td><td>{files_html if files_html else '—'}</td></tr>
</table>'''


# ═══════════════════════════════════════════════════
# KPI Table
# ═══════════════════════════════════════════════════
def _build_kpi_table(fin, metrics, periods):
    kpi_items = [
        ('total_assets', '资产总额', '元'),
        ('total_equity', '所有者权益', '元'),
        ('revenue', '营业收入', '元'),
        ('net_profit', '净利润', '元'),
        ('current_ratio', '流动比率', '倍'),
        ('debt_ratio', '资产负债率', '%'),
        ('roe', '净资产收益率(ROE)', '%'),
        ('gross_profit_margin', '毛利率', '%'),
    ]

    def fmt(v, unit=''):
        if v is None:
            return '<span style="color:#AAA">—</span>'
        if unit == '%':
            return f'{v*100:.2f}%' if 0 < abs(v) < 10 else f'{v:.2f}'
        if abs(v) >= 1e8:
            return f'{v/1e8:.2f} 亿元'
        if abs(v) >= 1e4:
            return f'{v/1e4:.2f} 万元'
        return f'{v:.2f}'

    rows = ''.join(f'<tr><td style="font-weight:bold;color:#111">{label}</td><td style="font-weight:bold;text-align:right;font-size:12pt;color:#000">{fmt(v)}</td></tr>'
                   for key, label, unit in kpi_items
                   for v in [(fin.get(key) if fin.get(key) is not None else metrics.get(key, {}).get('value'))])

    return f'''
<h2>二、核心财务指标</h2>
<div style="font-size:10pt;font-weight:bold;color:#444;margin-bottom:4pt">最新期数据{ '：' + periods[-1] if periods else ''}</div>
<table>
  <tr><th style="width:130pt">指标</th><th>数值</th></tr>
  {rows}
</table>'''


# ═══════════════════════════════════════════════════
# Six-dimension scores
# ═══════════════════════════════════════════════════
def _build_dimension_scores(dim_scores, weights, dim_labels, total_score, grade, gc):
    gcolor, gbg = gc

    def bar_row(dim):
        sc = dim_scores.get(dim, 0)
        lb = dim_labels.get(dim, dim)
        w = weights.get(dim, 0)
        pct = min(100, max(0, sc))
        bc = '#1D7A4C' if pct >= 70 else '#B8860B' if pct >= 50 else '#A32D2D'
        return f'''<tr>
  <td style="font-weight:bold;color:#111">{lb}</td>
  <td style="text-align:right;font-weight:bold;color:#000;font-size:12pt">{sc:.1f}</td>
  <td><div class="score-bg"><div class="score-fill" style="width:{int(pct)}%;background:{bc}"></div></div></td>
  <td style="text-align:center;color:#444;font-size:10pt">{int(w*100)}%</td></tr>'''

    rows = ''.join(bar_row(d) for d in dim_scores if d in dim_labels)
    return f'''
<h2>三、六维风险评分</h2>
<table style="table-layout:fixed">
  <colgroup><col style="width:90pt"/><col style="width:50pt"/><col style="width:auto"/><col style="width:45pt"/></colgroup>
  <tr><th>维度</th><th style="text-align:right">得分</th><th>评分条</th><th style="text-align:center">权重</th></tr>
  {rows}
  <tr class="total-row"><td style="font-weight:bold;font-size:12pt">综合评分</td>
    <td style="text-align:right;font-weight:bold;font-size:14pt;color:{gcolor}">{total_score:.1f}</td>
    <td style="font-weight:bold;font-size:12pt;color:{gcolor}">等级：{grade}</td><td></td></tr>
</table>'''


# ═══════════════════════════════════════════════════
# M-Score
# ═══════════════════════════════════════════════════
def _build_mscore_section(metrics):
    ms = metrics.get('m_score', {})
    if not ms or ms.get('value') is None:
        return ''

    value = ms['value']
    if value < -2.22:
        interp, color = '财务造假可能性低', '#1D7A4C'
    elif value > -1.78:
        interp, color = '财务造假可能性高', '#A32D2D'
    else:
        interp, color = '无法判断（警示区间）', '#B8860B'

    factors = [
        ('DSRI', '应收账款指数', '= (当期应收/收入) / (上期应收/收入)'),
        ('GMI', '毛利率指数', '= 上期毛利率 / 当期毛利率'),
        ('AQI', '资产质量指数', '= (1 - 长期资产/总资产)当期 / 上期'),
        ('SGI', '营收增长指数', '= 当期收入 / 上期收入'),
        ('DEPI', '折旧指数', '= 上期折旧率 / 当期折旧率'),
        ('SGAI', '销管费用指数', '= (当期销管费/收入) / (上期销管费/收入)'),
        ('TATA', '应计利润比率', '= (净利润 - 经营现金流) / 总资产'),
        ('LVGI', '财务杠杆指数', '= 当期负债率 / 上期负债率'),
    ]
    frows = ''
    for fid, fname, formula in factors:
        fv = ms.get(fid)
        if fv is None:
            continue
        is_ab = fv > 1.1 or fv < 0.9
        fc = '#A32D2D' if is_ab else '#333'
        ar = chr(8593) if fv > 1.0 else (chr(8595) if fv < 1.0 else chr(8594))
        frows += f'<tr><td style="font-weight:bold;font-size:11pt;color:{fc}">{fid}</td><td style="font-size:11pt">{fname}</td><td style="font-size:9pt;color:#444">{formula}</td><td style="text-align:right;font-weight:bold;font-size:11pt;color:{fc}">{ar} {fv:.4f}</td></tr>'

    return f'''
<h2>四、Beneish M-Score 财务造假预警</h2>
<table>
  <tr><td style="width:90pt;text-align:center;font-size:30pt;font-weight:bold;color:{color}">{value:.2f}</td>
  <td>
    <div style="font-weight:bold;color:{color};font-size:13pt">{interp}</div>
    <div style="margin-top:6pt;font-size:9pt;color:#333;line-height:1.7">
      <b>M-Score 公式：</b>M = -4.84 + 0.92xDSRI + 0.53xGMI + 0.40xAQI + 0.89xSGI + 0.12xDEPI - 0.17xSGAI + 4.68xTATA - 0.33xLVGI<br/>
      <b>阈值：</b>M &lt; -2.22 正常&nbsp;|&nbsp;-2.22 ~ -1.78 警示&nbsp;|&nbsp;M &gt; -1.78 高度怀疑
    </div>
  </td></tr>
</table>
<h3>各因子详情</h3>
<table style="table-layout:fixed">
  <colgroup><col style="width:48pt"/><col style="width:72pt"/><col style="width:auto"/><col style="width:58pt"/></colgroup>
  <tr><th>因子</th><th>名称</th><th>计算公式</th><th style="text-align:right">数值</th></tr>
  {frows}
</table>'''


# ═══════════════════════════════════════════════════
# Consistency check
# ═══════════════════════════════════════════════════
def _build_consistency_check(consistency_result):
    if not consistency_result:
        return '<h2>五、财务勾稽校验</h2><div style="color:#888">未执行财务勾稽校验。</div>'
    rows = ''
    for c in consistency_result:
        name = c.get('name', c.get('check', ''))
        st = c.get('status', c.get('result', ''))
        desc = c.get('description', c.get('detail', ''))
        sc = '#1D7A4C' if st in ('PASS', '一致', '正常') else '#A32D2D' if st in ('FAIL', '不一致', '异常') else '#B8860B'
        rows += f'<tr><td style="width:100pt;white-space:normal">{name}</td><td style="width:40pt;color:{sc};font-weight:bold">{st}</td><td style="font-size:8.5pt;color:#555">{desc}</td></tr>'
    return f'''
<h2>五、财务勾稽校验</h2>
<table><tr><th style="width:100pt">校验项目</th><th style="width:40pt">结果</th><th>说明</th></tr>{rows}</table>'''


# ═══════════════════════════════════════════════════
# Financial statements
# ═══════════════════════════════════════════════════
def _build_financial_tables(three_stmt, fin):
    def fmt_wan(v):
        return '<span style="color:#AAA">—</span>' if v is None or v == 0 else f'{v/1e4:.2f} 万'

    parts = ''

    # Balance sheet
    bs_cats = [
        ('资产', [('货币资金', 'cash'), ('交易性金融资产', 'trading_financial_assets'),
         ('应收账款', 'accounts_receivable'), ('其他应收款', 'other_receivables'),
         ('存出保证金', 'deposit_out'), ('存货', 'inventory'),
         ('流动资产合计', 'current_assets'), ('固定资产', 'fixed_assets'),
         ('无形资产', 'intangible_assets'), ('长期待摊费用', 'long_term_deferred_expense'),
         ('资产总计', 'total_assets')]),
        ('负债', [('短期借款', 'short_term_loans'), ('应付账款', 'accounts_payable'),
         ('应交税费', 'taxes_payable'), ('其他应付款', 'other_payables'),
         ('存入保证金', 'deposit_in'), ('流动负债合计', 'current_liabilities'),
         ('长期借款', 'long_term_loans'), ('负债合计', 'total_liabilities')]),
        ('所有者权益', [('实收资本', 'paid_in_capital'), ('资本公积', 'capital_reserve'),
         ('未分配利润', 'retained_earnings'), ('所有者权益合计', 'total_equity')]),
    ]
    bs_html = ''
    for cat, items in bs_cats:
        rows = ''
        for label, key in items:
            v = fin.get(key)
            tot = '合计' in label or '总计' in label
            rows += f'<tr{" class=\"total-row\"" if tot else ""}><td style="font-weight:bold;color:#111">{label}</td><td style="text-align:right;font-weight:bold;font-size:11pt">{fmt_wan(v)}</td></tr>'
        bs_html += f'<h3>{cat}</h3><table>{rows}</table>'
    if fin:
        parts += f'<h2>六、资产负债表</h2>{bs_html}'

    # Income statement
    inc_items = [('营业收入', 'revenue'), ('营业成本', 'cost_of_sales'),
                 ('税金及附加', 'tax_and_surcharges'), ('销售费用', 'selling_expense'),
                 ('管理费用', 'admin_expense'), ('财务费用', 'finance_cost'),
                 ('营业利润', 'operating_profit'), ('营业外收入', 'non_operating_income'),
                 ('营业外支出', 'non_operating_expense'),
                 ('利润总额', 'profit_before_tax'), ('所得税费用', 'income_tax'),
                 ('净利润', 'net_profit')]
    inc_rows = ''
    for label, key in inc_items:
        v = fin.get(key)
        hl = key in ('operating_profit', 'profit_before_tax', 'net_profit')
        inc_rows += f'<tr{" class=\"total-row\"" if hl else ""}><td style="width:200pt">{label}</td><td style="text-align:right">{fmt_wan(v)}</td></tr>'
    if fin:
        parts += f'<h2>七、利润表</h2><table>{inc_rows}</table>'

    return parts


# ═══════════════════════════════════════════════════
# Knowledge Base
# ═══════════════════════════════════════════════════
def _build_knowledge_base_section(metrics):
    all_rules = []
    for key, m in metrics.items():
        for rule in m.get('triggered_rules', []):
            all_rules.append((m.get('label', key), rule))

    if not all_rules:
        return '<h2>八、知识库评判结果</h2><div style="color:#1D7A4C;padding:10pt 0">未触发任何风险预警规则。</div>'

    rl_map = {'CRITICAL': '极高风险', 'HIGH': '高风险', 'MEDIUM': '中等风险', 'LOW': '低风险'}
    rows = ''
    for ml, rule in all_rules:
        lvl = rule.get('risk_level', 'LOW')
        rows += f'''<tr>
  <td style="font-weight:600;font-size:10pt">{ml}</td>
  <td style="font-weight:600;white-space:normal;word-wrap:break-word;font-size:10pt"><b>[{rule.get('id','')}]</b> {rule.get('name','')}</td>
  <td style="text-align:center;font-weight:bold;font-size:10pt">{rl_map.get(lvl, lvl)}</td>
  <td style="font-size:10pt;color:#333;white-space:normal;word-wrap:break-word;word-break:break-all">{rule.get('regulation','')}</td></tr>'''

    return f'''
<h2>八、知识库评判结果</h2>
<div style="font-size:10pt;font-weight:bold;color:#444;margin-bottom:4pt">共触发 {len(all_rules)} 条风险规则</div>
<table style="table-layout:fixed">
  <colgroup><col style="width:55pt"/><col style="width:140pt"/><col style="width:48pt"/><col style="width:auto"/></colgroup>
  <tr><th>指标</th><th>触发规则</th><th style="text-align:center">风险等级</th><th>监管依据</th></tr>
  {rows}
</table>'''


# ═══════════════════════════════════════════════════
# Credit Rating
# ═══════════════════════════════════════════════════
def _build_credit_rating_table():
    grades = [
        ('AAA', '90 - 100', '建议足额授信'),
        ('AA', '80 - 89', '建议正常授信'),
        ('A', '70 - 79', '审慎授信'),
        ('BBB', '60 - 69', '附条件授信'),
        ('BB', '50 - 59', '压缩授信额度'),
        ('B', '40 - 49', '建议拒绝或要求强担保'),
        ('CCC', '0 - 39', '拒绝授信（一票否决）'),
    ]
    rows = ''.join(f'<tr><td style="text-align:center;font-weight:bold;width:50pt">{g}</td><td style="text-align:center;width:60pt">{s}</td><td>{d}</td></tr>' for g, s, d in grades)
    return f'''
<h2>九、信用评级说明</h2>
<div style="font-size:9pt;color:#555;margin-bottom:6pt">本报告采用银行通用三级九等信用评级体系，综合评分由六维风险评估模型计算得出。</div>
<table>
  <tr><th style="width:50pt">等级</th><th style="width:60pt">评分区间</th><th>授信建议</th></tr>
  {rows}
</table>'''
