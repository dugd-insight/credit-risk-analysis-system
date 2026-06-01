# -*- coding: utf-8 -*-
"""
报告生成器
将分析结果生成为完整的 HTML 报告
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# 复用 risk_engine 的报告生成器
CURRENT_DIR = Path(__file__).parent.parent.parent / "risk_engine"
if CURRENT_DIR.exists():
    sys.path.insert(0, str(CURRENT_DIR))

try:
    from report_generator import generate_report as rg_generate
    from risk_analyzer import CREDIT_GRADES
    REPORT_ENGINE_READY = True
except ImportError:
    REPORT_ENGINE_READY = False


def generate_html_report(
    company_name: str,
    industry: str,
    analysis_result: Dict,
    output_path: str
) -> str:
    """
    生成完整的 HTML 报告

    Args:
        company_name: 企业名称
        industry: 行业分类
        analysis_result: analyze_company() 返回的分析结果
        output_path: 输出文件路径

    Returns:
        报告文件路径
    """
    if not REPORT_ENGINE_READY:
        return _generate_simple_report(company_name, industry, analysis_result, output_path)

    # 调用 risk_engine 的报告生成器
    try:
        # 从 period_details 中提取文件路径列表
        file_list = []
        period_details = analysis_result.get('period_details', {})
        for period_data in period_details.values():
            filepath = period_data.get('filepath', '')
            if filepath and filepath not in file_list:
                file_list.append(filepath)
        
        # 如果仍为空，尝试从 analysis_result 直接获取
        if not file_list:
            file_list = analysis_result.get('file_list', [])
        
        report_path = rg_generate(
            company_name=company_name,
            industry=industry,
            metrics=analysis_result.get('metrics', {}),
            score_result={
                'total_score': analysis_result.get('total_score', 0),
                'grade': analysis_result.get('grade', 'N/A'),
                'suggestion': analysis_result.get('suggestion', ''),
                'color': analysis_result.get('color', 'yellow'),
                'dimension_scores': analysis_result.get('dimension_scores', {}),
                'weights': analysis_result.get('weights', {}),
            },
            fin=analysis_result.get('financial', {}),
            fin_prev=None,
            tax=analysis_result.get('tax', {}),
            file_list=file_list,
            periods=analysis_result.get('periods', []),
            period_details=period_details,
            output_path=output_path,
            analysis_notes=analysis_result.get('analysis_notes', []),
            period_info=analysis_result.get('period_info', {}),
            three_stmt=analysis_result.get('three_stmt'),
            consistency_result=analysis_result.get('consistency_result', []),
        )
        return report_path
    except Exception as e:
        # 如果 risk_engine 报告生成失败，使用简化版本
        return _generate_simple_report(company_name, industry, analysis_result, output_path)


def _generate_simple_report(
    company_name: str,
    industry: str,
    analysis_result: Dict,
    output_path: str
) -> str:
    """生成简化版 HTML 报告（当分析引擎不可用时）"""

    total_score = analysis_result.get('total_score', 0)
    grade = analysis_result.get('grade', 'N/A')
    suggestion = analysis_result.get('suggestion', '')
    periods = analysis_result.get('periods', [])
    dim_scores = analysis_result.get('dimension_scores', {})

    grade_colors = {
        'green': ('#1a6b3a', '#eaf3de'),
        'yellow': ('#7a5c00', '#fef9e7'),
        'orange': ('#854f0b', '#fff0ec'),
        'red': ('#7a1010', '#fde8e8'),
    }
    g_color = grade_colors.get(analysis_result.get('color', 'yellow'), grade_colors['yellow'])

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>信贷风险分析报告 - {company_name}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif;
        background: #f4f5f7; color: #222; font-size: 14px; line-height: 1.6; }}
.container {{ max-width: 1120px; margin: 0 auto; padding: 24px 16px; }}
.card {{ background: #fff; border-radius: 12px; border: 0.5px solid #e5e7eb; padding: 24px; margin-bottom: 20px; }}
h1 {{ font-size: 20px; font-weight: 600; color: #111; margin-bottom: 4px; }}
h2 {{ font-size: 15px; font-weight: 500; color: #222; margin-bottom: 14px; padding-bottom: 8px; border-bottom: 1px solid #f0f0f0; }}
table {{ width: 100%; border-collapse: collapse; }}
th {{ font-size: 12px; font-weight: 500; color: #666; padding: 10px 8px; background: #f8f9fa; border-bottom: 1px solid #e5e7eb; text-align: left; }}
td {{ padding: 10px 8px; border-bottom: 0.5px solid #f0f0f0; }}
.score-bar {{ display: inline-flex; align-items: center; gap: 8px; }}
.score-bar-inner {{ width: 120px; height: 8px; background: #eee; border-radius: 4px; overflow: hidden; }}
</style>
</head>
<body>
<div class="container">

<!-- 封面 -->
<div class="card">
  <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
    <div>
      <div style="font-size: 12px; color: #888; margin-bottom: 4px;">银行信贷风险部 · 授信决策报告</div>
      <h1>📊 {company_name} 财务风险分析报告</h1>
      <div style="margin-top: 6px; font-size: 13px; color: #666;">行业分类：<b>{industry}</b></div>
    </div>
    <div style="text-align: center; min-width: 130px;">
      <div style="font-size: 44px; font-weight: 600; color: {g_color[0]}; background: {g_color[1]}; border: 2px solid {g_color[0]}; border-radius: 12px; padding: 8px 24px;">{grade}</div>
      <div style="font-size: 13px; color: {g_color[0]}; margin-top: 4px; font-weight: 500;">{total_score:.1f} 分</div>
    </div>
  </div>
  <div style="margin-top: 16px; padding: 12px 16px; background: {g_color[1]}; border-radius: 8px; border-left: 4px solid {g_color[0]};">
    <b style="color: {g_color[0]};">授信建议：</b>
    <span style="color: {g_color[0]}; font-size: 14px;">{suggestion}</span>
  </div>
</div>

<!-- 报告期 -->
<div class="card">
  <h2>📅 分析报告期</h2>
  <p>{', '.join(periods) if periods else '无'}</p>
</div>

<!-- 六维评分 -->
<div class="card">
  <h2>🎯 六维综合评分</h2>
  <table>
    <thead>
      <tr><th>维度</th><th>得分</th><th>分值</th></tr>
    </thead>
    <tbody>
'''

    dim_labels = {
        'solvency': '偿债能力',
        'profitability': '盈利能力',
        'cashflow': '现金流质量',
        'operations': '营运能力',
        'tax_compliance': '税务合规',
        'fraud_alert': '造假预警',
    }

    for dim, score in dim_scores.items():
        pct = min(100, max(0, score))
        bar_color = '#1D9E75' if pct >= 75 else ('#EF9F27' if pct >= 60 else ('#D85A30' if pct >= 40 else '#A32D2D'))
        label = dim_labels.get(dim, dim)
        html += f'''
      <tr>
        <td style="font-weight: 500;">{label}</td>
        <td>
          <div class="score-bar">
            <div class="score-bar-inner">
              <div style="width: {int(pct)}%; height: 100%; background: {bar_color};"></div>
            </div>
            <span style="font-size: 13px; color: {bar_color};">{score:.0f}分</span>
          </div>
        </td>
      </tr>'''

    html += '''
    </tbody>
  </table>
</div>

<!-- 信用评级说明 -->
<div class="card">
  <h2>🏆 信用评级说明</h2>
  <table>
    <thead>
      <tr><th>等级</th><th>分数区间</th><th>授信建议</th></tr>
    </thead>
    <tbody>
      <tr><td>AAA</td><td>90-100</td><td>建议足额授信</td></tr>
      <tr><td>AA</td><td>80-89</td><td>建议正常授信</td></tr>
      <tr><td>A</td><td>70-79</td><td>审慎授信</td></tr>
      <tr><td>BBB</td><td>60-69</td><td>附条件授信</td></tr>
      <tr><td>BB</td><td>50-59</td><td>压缩授信额度</td></tr>
      <tr><td>B</td><td>40-49</td><td>建议拒绝或强担保</td></tr>
      <tr><td>CCC</td><td>0-39</td><td>建议拒绝授信</td></tr>
    </tbody>
  </table>
</div>

<!-- 结尾 -->
<div class="card" style="font-size: 12px; color: #999; text-align: center;">
  本报告由信贷风险分析系统自动生成，仅供决策参考，不构成最终授信决定。<br>
  最终授信决策须经信贷委员会审批，并符合相关监管要求。<br>
  报告生成时间：''' + datetime.now().strftime('%Y年%m月%d日 %H:%M') + '''
</div>

</div>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)

    return output_path
