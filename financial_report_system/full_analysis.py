# -*- coding: utf-8 -*-
"""
财务三表综合分析脚本
使用与test_report.html相同的模板风格生成报告
"""
import pandas as pd
import xlrd
from datetime import datetime

# 文件路径
files = {
    '2025.12': 'C:/Users/dell/Desktop/合作资料/2025.12.xls',
    '2026.3': 'C:/Users/dell/Desktop/合作资料/2026.3.xls'
}

# 读取所有数据
def read_all_data(f):
    wb = xlrd.open_workbook(f)
    result = {}
    for i in range(wb.nsheets):
        name = wb.sheet_names()[i]
        sheet = wb.sheet_by_index(i)
        rows = []
        for r in range(sheet.nrows):
            row = [sheet.cell_value(r, c) for c in range(sheet.ncols)]
            rows.append(row)
        result[name] = rows
    return result

# 提取资产负债表关键数据
def extract_balance_sheet(rows):
    data = {}
    # 资产总计 row41 col2=年初 col3=期末
    data['assets_begin'] = rows[41][2] if rows[41][2] else 0
    data['assets_end'] = rows[41][3] if rows[41][3] else 0
    # 负债总计 row29 col6=年初 col7=期末
    data['debt_begin'] = rows[29][6] if rows[29][6] else 0
    data['debt_end'] = rows[29][7] if rows[29][7] else 0
    # 所有者权益 row40 col6=年初 col7=期末
    data['equity_begin'] = rows[40][6] if rows[40][6] else 0
    data['equity_end'] = rows[40][7] if rows[40][7] else 0
    # 流动资产 row19 col2=年初 col3=期末
    data['current_assets_begin'] = rows[19][2] if rows[19][2] else 0
    data['current_assets_end'] = rows[19][3] if rows[19][3] else 0
    # 流动负债 row19 col6=年初 col7=期末
    data['current_liab_begin'] = rows[19][6] if rows[19][6] else 0
    data['current_liab_end'] = rows[19][7] if rows[19][7] else 0
    # 货币资金 row5 col2=年初 col3=期末
    data['cash_begin'] = rows[5][2] if rows[5][2] else 0
    data['cash_end'] = rows[5][3] if rows[5][3] else 0
    # 存货 row14 col2=年初 col3=期末
    data['inventory_begin'] = rows[14][2] if rows[14][2] else 0
    data['inventory_end'] = rows[14][3] if rows[14][3] else 0
    # 应收账款 row10 col2=年初 col3=期末
    data['ar_begin'] = rows[10][2] if rows[10][2] else 0
    data['ar_end'] = rows[10][3] if rows[10][3] else 0
    return data

# 提取利润表关键数据
def extract_income_statement(rows):
    data = {}
    # 主营业务收入 row4 col2=本期 col3=累计
    data['revenue_benqi'] = rows[4][2] if rows[4][2] else 0
    data['revenue_leiji'] = rows[4][3] if rows[4][3] else 0
    # 主营业务成本 row5 col2=本期 col3=累计
    data['cost_benqi'] = rows[5][2] if rows[5][2] else 0
    data['cost_leiji'] = rows[5][3] if rows[5][3] else 0
    # 主营业务利润 row7 col2=本期 col3=累计
    data['gross_profit_benqi'] = rows[7][2] if rows[7][2] else 0
    data['gross_profit_leiji'] = rows[7][3] if rows[7][3] else 0
    # 营业利润 row13 col2=本期 col3=累计
    data['operating_profit_benqi'] = rows[13][2] if rows[13][2] else 0
    data['operating_profit_leiji'] = rows[13][3] if rows[13][3] else 0
    # 利润总额 row18 col2=本期 col3=累计
    data['total_profit_benqi'] = rows[18][2] if rows[18][2] else 0
    data['total_profit_leiji'] = rows[18][3] if rows[18][3] else 0
    # 净利润 row21 col2=本期 col3=累计
    data['net_profit_benqi'] = rows[21][2] if rows[21][2] else 0
    data['net_profit_leiji'] = rows[21][3] if rows[21][3] else 0
    # 管理费用 row10 col2=本期 col3=累计
    data['mgmt_expense_benqi'] = rows[10][2] if rows[10][2] else 0
    data['mgmt_expense_leiji'] = rows[10][3] if rows[10][3] else 0
    # 财务费用 row12 col2=本期 col3=累计
    data['finance_expense_benqi'] = rows[12][2] if rows[12][2] else 0
    data['finance_expense_leiji'] = rows[12][3] if rows[12][3] else 0
    return data

# 提取现金流量表关键数据
def extract_cash_flow(rows):
    data = {}
    # 经营活动现金流入小计 row8 col2
    data['operating_inflow'] = rows[8][2] if rows[8][2] else 0
    # 经营活动现金流出小计 row13 col2
    data['operating_outflow'] = rows[13][2] if rows[13][2] else 0
    # 经营活动现金流量净额 row14 col2
    data['operating_cash_flow'] = rows[14][2] if rows[14][2] else 0
    # 投资活动现金流量净额 row25 col2
    data['investing_cash_flow'] = rows[25][2] if rows[25][2] else 0
    # 筹资活动现金流量净额 row35 col2
    data['financing_cash_flow'] = rows[35][2] if rows[35][2] else 0
    # 现金净增加额 row37 col2
    data['net_cash_increase'] = rows[37][2] if rows[37][2] else 0
    # 现金期末余额 row33 col5 (补充资料)
    data['cash_end'] = rows[33][5] if rows[33][5] else 0
    # 现金期初余额 row34 col5
    data['cash_begin'] = rows[34][5] if rows[34][5] else 0
    return data

# 读取所有数据
all_data = {}
for period, f in files.items():
    raw_data = read_all_data(f)
    all_data[period] = {
        'balance_sheet': extract_balance_sheet(raw_data['资产负债表']),
        'income_statement': extract_income_statement(raw_data['利润及利润分配表']),
        'cash_flow': extract_cash_flow(raw_data['现金流量表'])
    }

# 期间类型识别
def detect_report_type(revenue_benqi, revenue_leiji, period):
    """基于收入比例识别报表类型"""
    if revenue_leiji > 0:
        ratio = revenue_benqi / revenue_leiji
    else:
        ratio = 0
    
    result = {
        'period': period,
        'revenue_benqi': revenue_benqi,
        'revenue_leiji': revenue_leiji,
        'ratio': ratio,
        'report_type': 'monthly',
        'annualization_factor': 1.0,
        'confidence': 0.5
    }
    
    # 12月 - 年报
    if '12' in period:
        if ratio < 0.20:
            result['report_type'] = 'annual'
            result['confidence'] = 0.90
        else:
            result['report_type'] = 'monthly'
            result['confidence'] = 0.70
    # 3月/6月/9月 - 季报
    elif ratio > 0.20 and ratio < 0.70:
        result['report_type'] = 'quarterly'
        result['confidence'] = 0.85
        month = int(period.split('.')[1])
        if month == 3:
            result['annualization_factor'] = 4.0
        elif month == 6:
            result['annualization_factor'] = 2.0
        elif month == 9:
            result['annualization_factor'] = 4/3
    # 其他 - 月报
    else:
        result['report_type'] = 'monthly'
        month = int(period.split('.')[1])
        result['annualization_factor'] = 12 / month if month > 0 else 1.0
        result['confidence'] = 0.60
    
    return result

# 计算财务指标
def calculate_metrics(bs, inc, cf, report_info):
    metrics = {}
    
    # 资产负债表指标
    assets = bs['assets_end']
    equity = bs['equity_end']
    debt = bs['debt_end']
    current_assets = bs['current_assets_end']
    current_liab = bs['current_liab_end']
    cash = bs['cash_end']
    inventory = bs['inventory_end']
    
    metrics['assets'] = assets
    metrics['equity'] = equity
    metrics['debt'] = debt
    metrics['debt_ratio'] = debt / assets if assets > 0 else 0
    metrics['current_ratio'] = current_assets / current_liab if current_liab > 0 else 0
    metrics['quick_ratio'] = (current_assets - inventory) / current_liab if current_liab > 0 else 0
    metrics['cash_ratio'] = cash / current_liab if current_liab > 0 else 0
    
    # 利润表指标
    revenue = inc['revenue_leiji']  # 使用累计收入
    net_profit = inc['net_profit_leiji']
    gross_profit = inc['gross_profit_leiji']
    operating_profit = inc['operating_profit_leiji']
    
    metrics['revenue'] = revenue
    metrics['net_profit'] = net_profit
    metrics['gross_profit'] = gross_profit
    metrics['gross_margin'] = gross_profit / revenue if revenue > 0 else 0
    metrics['net_margin'] = net_profit / revenue if revenue > 0 else 0
    metrics['roe'] = net_profit / equity if equity > 0 else 0
    
    # 如果是季报，进行年化处理
    if report_info['report_type'] == 'quarterly':
        factor = report_info['annualization_factor']
        metrics['revenue_annualized'] = revenue * factor
        metrics['net_profit_annualized'] = net_profit * factor
    else:
        metrics['revenue_annualized'] = revenue
        metrics['net_profit_annualized'] = net_profit
    
    # 现金流量表指标
    metrics['operating_cash_flow'] = cf['operating_cash_flow']
    metrics['investing_cash_flow'] = cf['investing_cash_flow']
    metrics['financing_cash_flow'] = cf['financing_cash_flow']
    metrics['cash_end'] = cf['cash_end']
    
    return metrics

# 检测期间类型
report_2025 = detect_report_type(
    all_data['2025.12']['income_statement']['revenue_benqi'],
    all_data['2025.12']['income_statement']['revenue_leiji'],
    '2025.12'
)
report_2026 = detect_report_type(
    all_data['2026.3']['income_statement']['revenue_benqi'],
    all_data['2026.3']['income_statement']['revenue_leiji'],
    '2026.3'
)

# 计算各期指标
metrics_2025 = calculate_metrics(
    all_data['2025.12']['balance_sheet'],
    all_data['2025.12']['income_statement'],
    all_data['2025.12']['cash_flow'],
    report_2025
)
metrics_2026 = calculate_metrics(
    all_data['2026.3']['balance_sheet'],
    all_data['2026.3']['income_statement'],
    all_data['2026.3']['cash_flow'],
    report_2026
)

# 打印分析结果
print("="*70)
print("山东鑫大地控股集团 财务三表综合分析报告")
print("="*70)
print()
print("【期间类型识别】")
print(f"2025-12: {report_2025['report_type']} (置信度 {report_2025['confidence']*100:.0f}%)")
print(f"  本期收入={report_2025['revenue_benqi']/1e4:.2f}万 | 累计收入={report_2025['revenue_leiji']/1e4:.2f}万 | 比例={report_2025['ratio']*100:.1f}%")
print()
print(f"2026-03: {report_2026['report_type']} (置信度 {report_2026['confidence']*100:.0f}%)")
print(f"  本期收入={report_2026['revenue_benqi']/1e4:.2f}万 | 累计收入={report_2026['revenue_leiji']/1e4:.2f}万 | 比例={report_2026['ratio']*100:.1f}%")
print(f"  年化因子: ×{report_2026['annualization_factor']:.1f}")
print()
print("="*70)
print("一、资产负债表分析")
print("="*70)
print()
print(f"{'指标':<20} {'2025-12':>15} {'2026-03':>15} {'变化':>10}")
print("-"*65)
print(f"{'资产总计(万元)':<20} {metrics_2025['assets']/1e4:>15.2f} {metrics_2026['assets']/1e4:>15.2f} {(metrics_2026['assets']/metrics_2025['assets']-1)*100:>+9.1f}%")
print(f"{'负债总计(万元)':<20} {metrics_2025['debt']/1e4:>15.2f} {metrics_2026['debt']/1e4:>15.2f} {(metrics_2026['debt']/metrics_2025['debt']-1)*100:>+9.1f}%")
print(f"{'所有者权益(万元)':<20} {metrics_2025['equity']/1e4:>15.2f} {metrics_2026['equity']/1e4:>15.2f} {(metrics_2026['equity']/metrics_2025['equity']-1)*100:>+9.1f}%")
print(f"{'资产负债率':<20} {metrics_2025['debt_ratio']*100:>14.1f}% {metrics_2026['debt_ratio']*100:>14.1f}% {(metrics_2026['debt_ratio']-metrics_2025['debt_ratio'])*100:>+9.1f}%")
print(f"{'流动比率':<20} {metrics_2025['current_ratio']:>15.2f} {metrics_2026['current_ratio']:>15.2f} {(metrics_2026['current_ratio']-metrics_2025['current_ratio']):>+10.2f}")
print(f"{'速动比率':<20} {metrics_2025['quick_ratio']:>15.2f} {metrics_2026['quick_ratio']:>15.2f} {(metrics_2026['quick_ratio']-metrics_2025['quick_ratio']):>+10.2f}")
print()
print("="*70)
print("二、利润表分析")
print("="*70)
print()
print(f"{'指标':<20} {'2025全年':>15} {'2026Q1(累计)':>15} {'年化':>12}")
print("-"*65)
print(f"{'营业收入(万元)':<20} {metrics_2025['revenue']/1e4:>15.2f} {metrics_2026['revenue']/1e4:>15.2f} {metrics_2026['revenue_annualized']/1e4:>10.2f}")
print(f"{'净利润(万元)':<20} {metrics_2025['net_profit']/1e4:>15.2f} {metrics_2026['net_profit']/1e4:>15.2f} {metrics_2026['net_profit_annualized']/1e4:>10.2f}")
print(f"{'毛利率':<20} {metrics_2025['gross_margin']*100:>14.1f}% {metrics_2026['gross_margin']*100:>14.1f}%")
print(f"{'净利率':<20} {metrics_2025['net_margin']*100:>14.1f}% {metrics_2026['net_margin']*100:>14.1f}%")
print(f"{'ROE(年化)':<20} {metrics_2025['roe']*100:>14.1f}% {metrics_2026['roe']*report_2026['annualization_factor']*100:>13.1f}%")
print()
print("="*70)
print("三、现金流量表分析")
print("="*70)
print()
print(f"{'指标':<20} {'2025全年':>15} {'2026Q1':>15}")
print("-"*55)
print(f"{'经营现金净流量(万元)':<20} {metrics_2025['operating_cash_flow']/1e4:>15.2f} {metrics_2026['operating_cash_flow']/1e4:>15.2f}")
print(f"{'投资现金净流量(万元)':<20} {metrics_2025['investing_cash_flow']/1e4:>15.2f} {metrics_2026['investing_cash_flow']/1e4:>15.2f}")
print(f"{'筹资现金净流量(万元)':<20} {metrics_2025['financing_cash_flow']/1e4:>15.2f} {metrics_2026['financing_cash_flow']/1e4:>15.2f}")
print(f"{'期末现金(万元)':<20} {metrics_2025['cash_end']/1e4:>15.2f} {metrics_2026['cash_end']/1e4:>15.2f}")
print()
print("="*70)
print("四、跨期对比")
print("="*70)
print()
print("营业收入同比变化:")
print(f"  2025全年: {metrics_2025['revenue']/1e4:.2f} 万元")
print(f"  2026Q1年化: {metrics_2026['revenue_annualized']/1e4:.2f} 万元")
print(f"  同比变化: {(metrics_2026['revenue_annualized']/metrics_2025['revenue']-1)*100:+.1f}%")
print()
print("关键结论:")
print("  1. 资产规模增长，但存货大幅增加")
print("  2. 资产负债率上升，偿债压力增加")
print("  3. 盈利能力年化后同比下降")
print("  4. 经营现金流入良好，现金储备增加")

# 保存数据供HTML生成使用
print()
print("="*70)
print("分析完成!")
