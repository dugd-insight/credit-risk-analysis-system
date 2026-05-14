# -*- coding: utf-8 -*-
"""
银行信贷风险分析系统 v3.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
新增 v3.0：
  - 三表全量解析（资产负债表 / 利润表 / 现金流量表）
  - 知识库评判依据内嵌报告（评分有据可查）
  - 财务三表勾稽校验
  - 多期对比 + 年化折算
  - 增强版 HTML 报告模板（与 full_analysis 风格一致）

用法：
  python main.py --files 2025.12.xls 2026.3.xls --company "山东鑫大地" --industry 制造业
  python main.py --dir data/ --company "企业名称" --industry 担保/金融服务
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(__file__))

from file_parser import load_all_files, load_files_multi_period
from risk_analyzer import calculate_metrics, compute_total_score
from report_generator import generate_report


def main():
    parser = argparse.ArgumentParser(description='银行信贷风险分析报告生成系统 v3.0')
    parser.add_argument('--dir',     default=None, help='财务文件目录（扫描所有 xls/xlsx）')
    parser.add_argument('--files',   nargs='+',    help='直接指定多个财务文件路径')
    parser.add_argument('--company', default='待分析企业', help='企业名称')
    parser.add_argument('--industry', default='制造业',
        choices=['制造业', '零售/批发', '担保/金融服务', '建筑/地产', '农业/食品', '通用'],
        help='行业分类')
    parser.add_argument('--output',  default=None, help='输出HTML文件路径')
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))

    print(f'\n{"=" * 62}')
    print(f'  银行信贷风险分析系统 v3.0  |  三表全量 + 知识库评判')
    print(f'{"=" * 62}')
    print(f'  企业：{args.company}')
    print(f'  行业：{args.industry}')

    # ─── Step 1：加载文件 ───────────────────────────────────
    print('\n[1/4] 扫描并解析财务文件（三表全量）...')

    if args.files:
        # 直接指定文件列表
        filepaths = [os.path.abspath(f) if not os.path.isabs(f) else f for f in args.files]
        print(f'  指定文件: {[os.path.basename(f) for f in filepaths]}')
        multi = load_files_multi_period(filepaths)
        data = {
            'financial': {},
            'tax': {},
            'periods': multi.get('periods', {}),
            'period_details': multi.get('periods', {}),
            'file_list': filepaths,
            'errors': multi.get('errors', []),
            'latest': {},
            'earliest': {},
        }
        if multi.get('latest_period'):
            lp = multi['latest_period']
            data['financial'] = multi['periods'][lp]['financial']
            data['latest']    = data['financial']
        if multi.get('earliest_period') and multi['earliest_period'] != multi.get('latest_period'):
            ep = multi['earliest_period']
            data['earliest'] = multi['periods'][ep]['financial']

    elif args.dir:
        data_dir = os.path.join(script_dir, args.dir) if not os.path.isabs(args.dir) else args.dir
        print(f'  数据目录: {data_dir}')
        data = load_all_files(data_dir)
    else:
        # 默认尝试上级目录的 data/
        data_dir = os.path.join(os.path.dirname(script_dir), 'data')
        print(f'  数据目录（默认）: {data_dir}')
        data = load_all_files(data_dir)

    periods = sorted(data.get('periods', {}).keys())
    print(f'  识别报告期: {periods}')
    print(f'  财务科目数: {len(data["financial"])}')
    print(f'  税务指标数: {len(data.get("tax", {}))}')
    if data.get('errors'):
        for e in data['errors']:
            print(f'  [WARN] {e}')

    if not data['financial']:
        print('\n[WARNING] 未能提取有效财务数据，使用演示数据...')
        data['financial'] = _demo_financial()
        data['latest'] = data['financial']
        data['earliest'] = {}

    # ─── Step 2：计算指标 ─────────────────────────────────
    print('\n[2/4] 计算财务指标（含知识库触发）...')
    fin_latest = data['financial']
    fin_prev   = data.get('earliest', {}) or {}

    if fin_prev and fin_prev != fin_latest and len(fin_prev) > 5:
        print(f'  启用跨期趋势分析（{len(periods)} 期数据）')
    else:
        fin_prev = None

    metrics = calculate_metrics(fin_latest, data.get('tax', {}), fin_prev)
    valid_metrics = {k: v for k, v in metrics.items()
                     if isinstance(v, dict) and v.get('value') is not None}
    print(f'  有效指标: {len(valid_metrics)} 项')

    # 汇报关键指标
    key_show = ['current_ratio', 'quick_ratio', 'debt_ratio',
                'net_profit_margin', 'gross_profit_margin', 'roe',
                'operating_cashflow']
    for k in key_show:
        if k in metrics and metrics[k].get('value') is not None:
            m   = metrics[k]
            v   = m['value']
            u   = m.get('unit', '')
            display = f'{v * 100:.2f}%' if u == '%' else (
                      f'{v / 1e4:.2f}万元' if (u == '元' and abs(v) >= 1e4) else f'{v:.3f}')
            flag = ' ⚠' if m.get('triggered_rules') else ''
            print(f'  {m["label"]}: {display}{flag}')

    total_alerts = sum(len(m.get('triggered_rules', []))
                       for m in metrics.values() if isinstance(m, dict))
    print(f'  知识库触发规则: {total_alerts} 条')

    # ─── Step 3：综合评分 ─────────────────────────────────
    print(f'\n[3/4] 综合评分（{args.industry}行业权重）...')
    score_result = compute_total_score(metrics, args.industry)
    print(f'  总分: {score_result["total_score"]:.1f}  等级: {score_result["grade"]}')
    print(f'  授信建议: {score_result["suggestion"]}')
    for dim, score in score_result['dimension_scores'].items():
        bar = '█' * int(score / 10) + '░' * (10 - int(score / 10))
        print(f'  {dim:15s} [{bar}] {score:.0f}分')

    # ─── Step 4：生成报告 ─────────────────────────────────
    print('\n[4/4] 生成 HTML 报告（知识库增强版）...')
    if args.output:
        out_path = args.output
    else:
        safe_name = args.company.replace('/', '_').replace('\\', '_').replace(' ', '_')
        out_dir   = os.path.join(os.path.dirname(script_dir), 'reports')
        os.makedirs(out_dir, exist_ok=True)
        out_path  = os.path.join(out_dir, f'report_{safe_name}.html')

    generate_report(
        company_name   = args.company,
        industry       = args.industry,
        metrics        = metrics,
        score_result   = score_result,
        fin            = fin_latest,
        fin_prev       = fin_prev,
        tax            = data.get('tax', {}),
        file_list      = data.get('file_list', []),
        periods        = periods,
        period_details = data.get('period_details', {}),
        output_path    = out_path,
    )

    print(f'\n{"=" * 62}')
    print(f'  ✅ 报告已生成: {out_path}')
    print(f'{"=" * 62}\n')
    return out_path


def _demo_financial():
    """演示数据（当无法读取文件时使用）"""
    return {
        'current_assets': 24521110, 'total_assets': 43858080,
        'cash': 7714340, 'accounts_receivable': 3005360,
        'inventory': 3896540, 'current_liabilities': 26729330,
        'total_liabilities': 26897500, 'total_equity': 16960580,
        'revenue': 58427880, 'cost_of_sales': 51495690,
        'gross_profit': 6783610, 'operating_profit': 487530,
        'profit_before_tax': 821810, 'income_tax': 0,
        'net_profit': 821810,
        'operating_cashflow': 5428670, 'investing_cashflow': -3143350,
        'financing_cashflow': 4208020,
    }


if __name__ == '__main__':
    main()
