# -*- coding: utf-8 -*-
import pandas as pd
import xlrd

files = {
    '2025.12': 'C:/Users/dell/Desktop/合作资料/2025.12.xls',
    '2026.3': 'C:/Users/dell/Desktop/合作资料/2026.3.xls'
}

data = {}
for period, f in files.items():
    wb = xlrd.open_workbook(f)
    sheets = {}
    for i in range(wb.nsheets):
        name = wb.sheet_names()[i]
        sheet = wb.sheet_by_index(i)
        # 读取为DataFrame
        rows = []
        for r in range(sheet.nrows):
            row = []
            for c in range(sheet.ncols):
                cell = sheet.cell_value(r, c)
                row.append(cell)
            rows.append(row)
        df = pd.DataFrame(rows)
        sheets[name] = df
    data[period] = sheets

# 打印利润表
print('='*60)
print('2025.12 利润表')
print('='*60)
print(data['2025.12']['利润及利润分配表'].to_string())

print()
print('='*60)
print('2026.3 利润表')
print('='*60)
print(data['2026.3']['利润及利润分配表'].to_string())

print()
print('='*60)
print('2025.12 现金流量表')
print('='*60)
print(data['2025.12']['现金流量表'].to_string())

print()
print('='*60)
print('2026.3 现金流量表')
print('='*60)
print(data['2026.3']['现金流量表'].to_string())
