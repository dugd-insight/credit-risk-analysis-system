# -*- coding: utf-8 -*-
"""
核心分析引擎
整合文件解析、指标计算、评分引擎
统一引用 financial_report_system/risk_engine 模块
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 动态计算 risk_engine 目录路径
# 期望路径结构: financial_report_system/app/core/analyzer.py
#               financial_report_system/risk_engine/
THIS_FILE = Path(__file__).resolve()  # 解析符号链接
CORE_DIR = THIS_FILE.parent            # = app/core/
APP_DIR = CORE_DIR.parent             # = app/
PROJECT_ROOT = APP_DIR.parent         # = financial_report_system/
RISK_ENGINE_DIR = PROJECT_ROOT / "risk_engine"

# 添加到 Python 路径
if str(RISK_ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(RISK_ENGINE_DIR))

# 导入分析模块
try:
    from file_parser import load_all_files, load_files_multi_period, extract_three_statements, check_cross_statement_consistency
    from risk_analyzer import calculate_metrics, compute_total_score
    from knowledge_base import KNOWLEDGE_BASE
    ENGINE_IMPORTED = True
except ImportError as e:
    ENGINE_IMPORTED = False
    IMPORT_ERROR = str(e)


def analyze_company(
    file_paths: List[str],
    company_name: str,
    industry: str,
    mode: str = "files"
) -> Dict:
    """
    核心分析函数

    Args:
        file_paths: 文件路径列表（mode=files）或目录路径列表（mode=directory）
        company_name: 企业名称
        industry: 行业分类
        mode: "files" - 直接分析文件列表, "directory" - 分析目录下所有文件

    Returns:
        包含完整分析结果的字典
    """
    if not ENGINE_IMPORTED:
        return _mock_analysis(company_name, industry, f"导入失败: {IMPORT_ERROR}")

    # 确定数据目录
    if mode == "directory" and file_paths:
        data_dir = file_paths[0]
        temp_dir = None
    else:
        # 创建临时目录存放文件
        import tempfile
        temp_dir = tempfile.mkdtemp()
        import shutil
        for fp in file_paths:
            shutil.copy(fp, os.path.join(temp_dir, os.path.basename(fp)))
        data_dir = temp_dir

    try:
        # 1. 加载并解析文件
        data = load_all_files(data_dir)

        financial = data.get('financial', {})
        tax = data.get('tax', {})
        periods = sorted(data.get('periods', {}).keys())
        period_details = data.get('periods', {})
        analysis_notes = data.get('analysis_notes', [])
        
        # 提取文件路径列表（用于报告展示）
        file_list = data.get('file_list', [])

        if not financial:
            return {
                "success": False,
                "error": "未能从文件中提取到有效的财务数据",
                "company_name": company_name,
                "industry": industry,
            }

        # 2. 获取最新期和最早期数据（使用年化后的数据）
        fin_latest = data.get('latest', {})
        fin_prev = data.get('earliest', {}) if len(periods) > 1 else None
        
        # 提取期间信息
        latest_period_info = {}
        prev_period_info = {}
        if len(periods) >= 1:
            latest_period_info = period_details.get(periods[-1], {}).get('period_info', {})
        if len(periods) >= 2:
            prev_period_info = period_details.get(periods[0], {}).get('period_info', {})

        # 3. 计算指标
        metrics = calculate_metrics(fin_latest, tax, fin_prev)

        # 4. 计算综合评分
        score_result = compute_total_score(metrics, industry)

        # 5. 构建返回结果
        result = {
            "success": True,
            "company_name": company_name,
            "industry": industry,
            "periods": periods,
            "period_details": period_details,
            "financial": financial,
            "tax": tax,
            "analysis_notes": analysis_notes,
            "metrics": metrics,
            "total_score": score_result.get("total_score", 0),
            "grade": score_result.get("grade", "N/A"),
            "suggestion": score_result.get("suggestion", ""),
            "color": score_result.get("color", "yellow"),
            "dimension_scores": score_result.get("dimension_scores", {}),
            "weights": score_result.get("weights", {}),
            "veto": score_result.get("veto", False),
            # 新增：文件列表
            "file_list": file_list,
            # 新增：期间类型信息
            "period_info": {
                "latest": latest_period_info,
                "previous": prev_period_info,
            },
            "annualization": {
                "enabled": True,
                "latest_type": latest_period_info.get('report_type', 'unknown'),
                "previous_type": prev_period_info.get('report_type', 'unknown'),
            }
        }
        
        # 6. 提取三表数据并进行勾稽校验（v3.0新增）
        if periods:
            latest_period = periods[-1]
            latest_fp = period_details.get(latest_period, {}).get('filepath', '')
            if latest_fp and os.path.exists(latest_fp):
                try:
                    three_stmt = extract_three_statements(latest_fp)
                    result['three_stmt'] = three_stmt
                    # 执行三表勾稽校验
                    consistency_result = check_cross_statement_consistency(three_stmt)
                    result['consistency_result'] = consistency_result
                except Exception as e:
                    import traceback
                    print(f"三表提取/校验失败: {e}")
                    result['three_stmt'] = {}
                    result['consistency_result'] = []
        
        return result

    except Exception as e:
        import traceback
        return {
            "success": False,
            "error": f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}",
            "company_name": company_name,
            "industry": industry,
        }
    finally:
        # 清理临时目录
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir, ignore_errors=True)


def _mock_analysis(company_name: str, industry: str, error: str = "") -> Dict:
    """当分析引擎未正确导入时的模拟结果"""
    return {
        "success": False,
        "error": f"分析引擎未正确导入，请检查 risk_engine 模块\n{error}",
        "company_name": company_name,
        "industry": industry,
        "total_score": 0,
        "grade": "N/A",
        "suggestion": "系统配置错误",
        "periods": [],
        "dimension_scores": {},
    }


def get_engine_status() -> Dict:
    """获取分析引擎状态"""
    return {
        "engine_imported": ENGINE_IMPORTED,
        "risk_engine_path": str(RISK_ENGINE_DIR),
        "path_exists": RISK_ENGINE_DIR.exists(),
    }
