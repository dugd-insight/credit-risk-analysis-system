# -*- coding: utf-8 -*-
import pandas as pd

files = {
    '2025.12': 'C:/Users/dell/Desktop/合作资料/2025.12.xls',
    '2026.3': 'C:/Users/dell/Desktop/合作资料/2026.3.xls'
}

data = {}
for period, f in files.items():
    df = pd.read_excel(f, header=None, engine='xlrd')
    data[period] = df

def extract_bs(df):
    result = {}
    # 资产总计 row41 col2=年初 col3=期末
    result['assets_begin'] = float(df.iloc[41, 2]) if pd.notna(df.iloc[41, 2]) else 0
    result['assets_end'] = float(df.iloc[41, 3]) if pd.notna(df.iloc[41, 3]) else 0
    # 负债总计 row29 col6=年初 col7=期末
    result['debt_begin'] = float(df.iloc[29, 6]) if pd.notna(df.iloc[29, 6]) else 0
    result['debt_end'] = float(df.iloc[29, 7]) if pd.notna(df.iloc[29, 7]) else 0
    # 所有者权益 row40 col6=年初 col7=期末
    result['equity_begin'] = float(df.iloc[40, 6]) if pd.notna(df.iloc[40, 6]) else 0
    result['equity_end'] = float(df.iloc[40, 7]) if pd.notna(df.iloc[40, 7]) else 0
    # 流动资产 row19 col2=年初 col3=期末
    result['current_assets_begin'] = float(df.iloc[19, 2]) if pd.notna(df.iloc[19, 2]) else 0
    result['current_assets_end'] = float(df.iloc[19, 3]) if pd.notna(df.iloc[19, 3]) else 0
    # 流动负债 row19 col6=年初 col7=期末
    result['current_liab_begin'] = float(df.iloc[19, 6]) if pd.notna(df.iloc[19, 6]) else 0
    result['current_liab_end'] = float(df.iloc[19, 7]) if pd.notna(df.iloc[19, 7]) else 0
    # 货币资金 row5 col2=年初 col3=期末
    result['cash_begin'] = float(df.iloc[5, 2]) if pd.notna(df.iloc[5, 2]) else 0
    result['cash_end'] = float(df.iloc[5, 3]) if pd.notna(df.iloc[5, 3]) else 0
    # 存货 row14 col2=年初 col3=期末
    result['inventory_begin'] = float(df.iloc[14, 2]) if pd.notna(df.iloc[14, 2]) else 0
    result['inventory_end'] = float(df.iloc[14, 3]) if pd.notna(df.iloc[14, 3]) else 0
    # 应收账款 row10 col2=年初 col3=期末
    result['ar_begin'] = float(df.iloc[10, 2]) if pd.notna(df.iloc[10, 2]) else 0
    result['ar_end'] = float(df.iloc[10, 3]) if pd.notna(df.iloc[10, 3]) else 0
    # 未分配利润 row39 col6=年初 col7=期末
    result['profit_begin'] = float(df.iloc[39, 6]) if pd.notna(df.iloc[39, 6]) else 0
    result['profit_end'] = float(df.iloc[39, 7]) if pd.notna(df.iloc[39, 7]) else 0
    # 实收资本 row33 col6=年初 col7=期末
    result['capital_begin'] = float(df.iloc[33, 6]) if pd.notna(df.iloc[33, 6]) else 0
    result['capital_end'] = float(df.iloc[33, 7]) if pd.notna(df.iloc[33, 7]) else 0
    return result

d2025 = extract_bs(data['2025.12'])
d2026 = extract_bs(data['2026.3'])

print('=' * 60)
print('山东鑫大地控股集团 资产负债表分析报告')
print('=' * 60)
print()
print('【报告期间】')
print('  2025年12月（年报）')
print('  2026年3月（Q1季报）')
print()
print('=' * 60)
print('一、核心财务指标')
print('=' * 60)
print()
print('1. 资产规模')
print('   | 指标              | 2025年末    | 2026.Q1    | 变化      |')
print('   |' + '-' * 60 + '|')
print("   | 资产总计(亿元)    | {:>10.2f} | {:>10.2f} | {:>8.1f}% |".format(
    d2025['assets_end']/1e8, d2026['assets_end']/1e8, (d2026['assets_end']/d2025['assets_end']-1)*100))
print("   | 资产年初数(亿元)  | {:>10.2f} | {:>10.2f} | {:>8.1f}% |".format(
    d2025['assets_begin']/1e8, d2026['assets_begin']/1e8, (d2026['assets_begin']/d2025['assets_begin']-1)*100))
print()
print('2. 负债情况')
print("   | 负债总计(亿元)    | {:>10.2f} | {:>10.2f} | {:>8.1f}% |".format(
    d2025['debt_end']/1e8, d2026['debt_end']/1e8, (d2026['debt_end']/d2025['debt_end']-1)*100))
debt_ratio_2025 = d2025['debt_end']/d2025['assets_end']*100
debt_ratio_2026 = d2026['debt_end']/d2026['assets_end']*100
debt_ratio_change = debt_ratio_2026 - debt_ratio_2025
print("   | 资产负债率        | {:>10.1f}% | {:>9.1f}% | {:>7.1f}% |".format(
    debt_ratio_2025, debt_ratio_2026, debt_ratio_change))
print()
print('3. 所有者权益')
print("   | 所有者权益(亿元)  | {:>10.2f} | {:>10.2f} | {:>8.1f}% |".format(
    d2025['equity_end']/1e8, d2026['equity_end']/1e8, (d2026['equity_end']/d2025['equity_end']-1)*100))
print("   | 实收资本(亿元)    | {:>10.2f} | {:>10.2f} | {:>8.1f}% |".format(
    d2025['capital_end']/1e8, d2026['capital_end']/1e8, (d2026['capital_end']/d2025['capital_end']-1)*100))
print("   | 未分配利润(亿元)  | {:>10.2f} | {:>10.2f} | {:>8.1f}% |".format(
    d2025['profit_end']/1e8, d2026['profit_end']/1e8, (d2026['profit_end']/d2025['profit_end']-1)*100))
print()
print('=' * 60)
print('二、偿债能力分析')
print('=' * 60)
print()
cr_2025 = d2025['current_assets_end'] / d2025['current_liab_end']
cr_2026 = d2026['current_assets_end'] / d2026['current_liab_end']
print('流动比率（流动资产/流动负债）:')
print('  2025年末: {:.2f} (参考值>1.5)'.format(cr_2025))
print('  2026.Q1: {:.2f}'.format(cr_2026))
print('  结论: {}'.format('良好' if cr_2026 >= 1 else '偏弱'))
print()
qr_2025 = (d2025['current_assets_end'] - d2025['inventory_end']) / d2025['current_liab_end']
qr_2026 = (d2026['current_assets_end'] - d2026['inventory_end']) / d2026['current_liab_end']
print('速动比率（(流动资产-存货)/流动负债）:')
print('  2025年末: {:.2f} (参考值>1.0)'.format(qr_2025))
print('  2026.Q1: {:.2f}'.format(qr_2026))
print('  结论: {}'.format('良好' if qr_2026 >= 1 else '偏弱'))
print()
print('=' * 60)
print('三、资产结构分析')
print('=' * 60)
print()
print('1. 流动资产:')
print('   2025年末: {:.2f}亿元 ({:.1f}%)'.format(d2025['current_assets_end']/1e8, d2025['current_assets_end']/d2025['assets_end']*100))
print('   2026.Q1: {:.2f}亿元 ({:.1f}%)'.format(d2026['current_assets_end']/1e8, d2026['current_assets_end']/d2026['assets_end']*100))
print()
print('2. 货币资金:')
print('   2025年末: {:.2f}亿元 ({:.1f}%)'.format(d2025['cash_end']/1e8, d2025['cash_end']/d2025['assets_end']*100))
print('   2026.Q1: {:.2f}亿元 ({:.1f}%)'.format(d2026['cash_end']/1e8, d2026['cash_end']/d2026['assets_end']*100))
print()
print('3. 存货:')
print('   2025年末: {:.2f}亿元 ({:.1f}%)'.format(d2025['inventory_end']/1e8, d2025['inventory_end']/d2025['assets_end']*100))
print('   2026.Q1: {:.2f}亿元 ({:.1f}%)'.format(d2026['inventory_end']/1e8, d2026['inventory_end']/d2026['assets_end']*100))
print('   变化: {:+.1f}%'.format((d2026['inventory_end']/d2025['inventory_end']-1)*100))
print()
print('4. 应收账款:')
print('   2025年末: {:.2f}亿元 ({:.1f}%)'.format(d2025['ar_end']/1e8, d2025['ar_end']/d2025['assets_end']*100))
print('   2026.Q1: {:.2f}亿元 ({:.1f}%)'.format(d2026['ar_end']/1e8, d2026['ar_end']/d2026['assets_end']*100))
print('   变化: {:+.1f}%'.format((d2026['ar_end']/d2025['ar_end']-1)*100))
print()
print('=' * 60)
print('四、跨期对比总结')
print('=' * 60)
print()
print('资产变化: 环比+{:.1f}%, 年化同比+{:.1f}%'.format(
    (d2026['assets_end']/d2025['assets_end']-1)*100,
    (d2026['assets_end']*4/d2025['assets_end']-1)*100))
print('负债变化: 环比+{:.1f}%'.format((d2026['debt_end']/d2025['debt_end']-1)*100))
print('资产负债率: {:.1f}% -> {:.1f}%'.format(debt_ratio_2025, debt_ratio_2026))
print('流动比率: {:.2f} -> {:.2f}'.format(cr_2025, cr_2026))
print('货币资金: {:.2f} -> {:.2f}亿元 ({:+.1f}%)'.format(
    d2025['cash_end']/1e8, d2026['cash_end']/1e8, (d2026['cash_end']/d2025['cash_end']-1)*100))
print('存货: {:.2f} -> {:.2f}亿元 ({:+.1f}%)'.format(
    d2025['inventory_end']/1e8, d2026['inventory_end']/1e8, (d2026['inventory_end']/d2025['inventory_end']-1)*100))
print('未分配利润: {:.2f} -> {:.2f}亿元 ({:+.1f}%)'.format(
    d2025['profit_end']/1e8, d2026['profit_end']/1e8, (d2026['profit_end']/d2025['profit_end']-1)*100))
