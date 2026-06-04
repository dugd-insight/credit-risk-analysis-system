# -*- coding: utf-8 -*-
"""
信贷风险分析系统 - FastAPI 应用入口
支持文件上传、多期分析、行业差异化评分、异步任务处理
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.requests import Request
from starlette.responses import Response
import os
import uuid
import shutil
import time
import traceback
from pathlib import Path
from typing import List, Optional

from .core.analyzer import analyze_company
from .core.report_generator import generate_html_report
from .config import get_config, config
from .tasks import task_manager, get_task_manager, TaskStatus
from .pdf_report import generate_pdf_report as generate_professional_pdf

# PDF生成
try:
    import xhtml2pdf.pisa as pisa
    from reportlab.pdfbase import pdfmetrics
    # 使用 reportlab 内置的 CID 中文字体（解决 xhtml2pdf 中文乱码问题）

    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    _cid_fonts = ['STSong-Light', 'HeiseiMin-W3', 'HeiseiKakuGo-W5', 'MSung-Light']
    _cid_registered = []
    for _fn in _cid_fonts:
        try:
            pdfmetrics.registerFont(UnicodeCIDFont(_fn))
            _cid_registered.append(_fn)
        except Exception:
            pass
    PDF_READY = True
except ImportError:
    PDF_READY = False


def _prepare_pdf_html(html: str) -> str:
    """将 HTML 报告转换为适合 PDF 生成的版本（注入 CID 字体、移除不兼容元素）"""
    import re

    # 移除 Chart.js 脚本和 Canvas 元素（PDF 不支持）
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    cleaned = re.sub(r'<canvas[^>]*>.*?</canvas>', '', cleaned, flags=re.DOTALL)

    # 注入 CID 字体样式和 PDF 布局配置
    # 注意：@page 中不支持 @top-center/@bottom-center 等 margin box（xhtml2pdf 限制）
    pdf_style = (
        '<style>'
        'body{font-family:STSong-Light,HeiseiMin-W3,HeiseiKakuGo-W5,MSung-Light,sans-serif!important;font-size:11pt}'
        'h1,h2,h3,th,td,span,div,p{font-family:STSong-Light,HeiseiMin-W3,HeiseiKakuGo-W5,MSung-Light,sans-serif!important}'
        '@page{size:A4;margin:1.5cm 1.2cm}'
        '.card{break-inside:avoid;page-break-inside:avoid}'
        '.container{max-width:100%!important}'
        'canvas{display:none!important}'
        '</style>'
    )
    cleaned = cleaned.replace('</head>', pdf_style + '</head>')

    return cleaned

# ─────────────────────────────────────────────
# 应用初始化
# ─────────────────────────────────────────────

app = FastAPI(
    title="信贷风险分析系统",
    description="银行信贷风险分析报告生成系统，支持多期财务报表分析",
    version="3.0"
)

# 加载配置
cfg = get_config()

# 静态文件和模板
BASE_DIR = cfg.paths.base_dir
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# 目录确保
UPLOAD_DIR = cfg.paths.upload_dir
REPORT_DIR = cfg.paths.report_dir


# ─────────────────────────────────────────────
# 首页 - 上传表单
# ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def home(response: Response):
    """返回上传表单页面（强制不缓存）"""
    # 应用缓存控制
    for key, value in cfg.get_cache_headers().items():
        response.headers[key] = value

    index_path = BASE_DIR / "templates" / "index.html"
    if index_path.exists():
        with open(index_path, "r", encoding="utf-8") as f:
            html = f.read()
            # 注入版本号防止缓存
            html = html.replace('<html lang="zh-CN">', f'<html lang="zh-CN">\n<!-- v{cfg.cache.version} -->')
            return html

    # 内联备用页面
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>信贷风险分析系统 v{cfg.cache.version}</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                   max-width: 800px; margin: 50px auto; padding: 20px; background: #f5f5f5; }}
            .container {{ background: white; padding: 40px; border-radius: 12px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
            h1 {{ color: #1a1a1a; margin-bottom: 30px; }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 8px; font-weight: 500; color: #333; }}
            input[type="text"], select {{ width: 100%; padding: 12px; border: 1px solid #ddd; border-radius: 6px; font-size: 14px; }}
            input[type="file"] {{ width: 100%; padding: 10px; border: 2px dashed #ddd; border-radius: 6px; }}
            button {{ background: #4F46E5; color: white; padding: 14px 30px; border: none; border-radius: 8px;
                     font-size: 16px; cursor: pointer; width: 100%; }}
            button:hover {{ background: #4338CA; }}
            .note {{ font-size: 12px; color: #666; margin-top: 5px; }}
            .industry-info {{ background: #f0f9ff; padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🏦 信贷风险分析系统 v{cfg.cache.version}</h1>
            <div class="industry-info">
                <b>支持行业：</b>制造业、零售/批发、担保/金融服务、建筑/地产、农业/食品、通用
            </div>
            <form id="analyzeForm">
                <div class="form-group">
                    <label>企业名称 *</label>
                    <input type="text" name="company_name" id="companyName" required placeholder="请输入企业全称">
                </div>
                <div class="form-group">
                    <label>行业分类 *</label>
                    <select name="industry" id="industry" required>
                        <option value="担保/金融服务">担保/金融服务</option>
                        <option value="制造业">制造业</option>
                        <option value="零售/批发">零售/批发</option>
                        <option value="建筑/地产">建筑/地产</option>
                        <option value="农业/食品">农业/食品</option>
                        <option value="通用">通用</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>上传财务报表 *（支持多文件）</label>
                    <input type="file" name="files" id="fileInput" multiple accept=".xls,.xlsx" required>
                    <div class="note">支持多期数据上传（不同报告期），系统会自动识别并对比分析</div>
                </div>
                <button type="submit" id="submitBtn">🔍 开始分析</button>
            </form>
        </div>
        <script>
            document.getElementById('analyzeForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                const btn = document.getElementById('submitBtn');
                const companyName = document.getElementById('companyName').value;
                const industry = document.getElementById('industry').value;
                const files = document.getElementById('fileInput').files;

                if (files.length === 0) {{
                    alert('请选择至少一个财务文件');
                    return;
                }}

                btn.disabled = true;
                btn.textContent = '分析中，请稍候...';

                const formData = new FormData();
                formData.append('company_name', companyName);
                formData.append('industry', industry);
                for (let i = 0; i < files.length; i++) {{
                    formData.append('files', files[i]);
                }}

                try {{
                    const response = await fetch('/api/analyze', {{
                        method: 'POST',
                        body: formData
                    }});
                    const data = await response.json();

                    if (data.success) {{
                        // 跳转到报告页面
                        window.location.href = data.report_url;
                    }} else {{
                        alert(data.detail || '分析失败');
                        btn.disabled = false;
                        btn.textContent = '🔍 开始分析';
                    }}
                }} catch (error) {{
                    alert('网络错误: ' + error.message);
                    btn.disabled = false;
                    btn.textContent = '🔍 开始分析';
                }}
            }});
        </script>
    </body>
    </html>
    """


# ─────────────────────────────────────────────
# 异步分析接口 - 创建任务
# ─────────────────────────────────────────────

@app.post("/api/analyze-async")
async def analyze_async(
    company_name: str = Form(...),
    industry: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    异步分析接口 - 创建分析任务并返回任务ID
    前端通过任务ID轮询获取进度和结果
    """
    # 验证文件
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个财务文件")

    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in cfg.files.allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {f.filename}")

    # 创建任务
    task_id = task_manager.create_task()

    # 创建临时目录
    session_id = str(uuid.uuid4())[:8]
    work_dir = UPLOAD_DIR / session_id
    work_dir.mkdir(exist_ok=True)

    # 保存文件
    saved_files = []
    try:
        for f in files:
            file_path = work_dir / f.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved_files.append(str(file_path))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"文件保存失败: {str(e)}")

    # 提交异步任务
    task_manager.submit_task(
        task_id,
        _run_analysis_task,
        task_id=task_id,
        file_paths=saved_files,
        company_name=company_name,
        industry=industry,
        work_dir=str(work_dir)
    )

    return {
        "success": True,
        "task_id": task_id,
        "message": "任务已创建，正在分析中...",
        "poll_url": f"/api/task/{task_id}",
    }


def _run_analysis_task(
    task_id: str,
    file_paths: List[str],
    company_name: str,
    industry: str,
    work_dir: str,
    _progress_callback=None
) -> dict:
    """
    执行分析任务的内部函数（在线程池中运行）
    """
    task_info = task_manager.get_task(task_id)
    progress = _progress_callback

    try:
        # 进度回调包装
        def update_progress(p: int, msg: str = ""):
            if progress:
                progress(p, msg)
            elif task_info:
                task_info.update_progress(p, msg)

        update_progress(10, "正在解析财务文件...")

        # 调用分析引擎
        result = analyze_company(file_paths, company_name, industry)

        update_progress(50, "财务数据解析完成，正在计算指标...")

        if not result.get("success"):
            return {
                "success": False,
                "error": result.get("error", "分析失败"),
                "company_name": company_name,
                "industry": industry,
            }

        update_progress(70, "指标计算完成，正在生成报告...")

        # 生成HTML报告
        session_id = task_id
        report_filename = f"{company_name}_{session_id}.html"
        report_path = REPORT_DIR / report_filename

        generate_html_report(
            company_name=company_name,
            industry=industry,
            analysis_result=result,
            output_path=str(report_path)
        )

        update_progress(85, "HTML报告生成完成...")

        # 生成PDF（使用专业PDF报告生成器）
        pdf_path = None
        if PDF_READY and cfg.report.pdf_enabled and report_path.exists():
            try:
                pdf_filename = f"{company_name}_{session_id}.pdf"
                pdf_path = REPORT_DIR / pdf_filename
                # 先生成 PDF 优化的 HTML
                pdf_html_path = REPORT_DIR / f"_{company_name}_{session_id}_pdf.html"
                generate_professional_pdf(
                    company_name=company_name,
                    industry=industry,
                    analysis_result=result,
                    output_path=str(pdf_html_path),
                )
                # 用 xhtml2pdf 转为 PDF
                with open(pdf_html_path, 'r', encoding='utf-8') as f:
                    pdf_html = f.read()
                with open(pdf_path, 'wb') as pdf_file:
                    pisa.CreatePDF(pdf_html, pdf_file, encoding='utf-8')
                # 清理临时 HTML
                if pdf_html_path.exists():
                    pdf_html_path.unlink()
            except Exception as pdf_err:
                print(f"PDF生成失败: {pdf_err}")
                import traceback
                traceback.print_exc()
                pdf_path = None

        update_progress(95, "报告生成完成！")

        # 清理临时文件
        shutil.rmtree(work_dir, ignore_errors=True)

        return {
            "success": True,
            "report_url": f"/api/report/{report_filename}",
            "pdf_url": f"/api/report/{pdf_filename}" if pdf_path and pdf_path.exists() else None,
            "summary": {
                "company_name": company_name,
                "industry": industry,
                "total_score": result.get("total_score", 0),
                "grade": result.get("grade", "N/A"),
                "suggestion": result.get("suggestion", ""),
                "periods": result.get("periods", []),
                "dimension_scores": result.get("dimension_scores", {}),
            }
        }

    except Exception as e:
        error_msg = f"分析过程出错: {str(e)}\n{traceback.format_exc()}"
        return {
            "success": False,
            "error": error_msg,
            "company_name": company_name,
            "industry": industry,
        }


# ─────────────────────────────────────────────
# 任务状态查询接口
# ─────────────────────────────────────────────

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """
    查询任务状态和结果
    前端轮询此接口获取进度
    """
    status = task_manager.get_task_status(task_id)

    if status is None:
        raise HTTPException(status_code=404, detail="任务不存在或已过期")

    return JSONResponse(content=status)


# ─────────────────────────────────────────────
# 同步分析接口 - 保留原有接口
# ─────────────────────────────────────────────

@app.post("/api/analyze")
async def analyze(
    company_name: str = Form(...),
    industry: str = Form(...),
    files: List[UploadFile] = File(...)
):
    """
    同步分析接口 - 等待分析完成返回结果
    适用于文件较小、分析较快的情况
    """
    # 验证文件
    if not files:
        raise HTTPException(status_code=400, detail="请上传至少一个财务文件")

    for f in files:
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in cfg.files.allowed_extensions:
            raise HTTPException(status_code=400, detail=f"不支持的文件格式: {f.filename}")

    # 创建临时目录
    session_id = str(uuid.uuid4())[:8]
    work_dir = UPLOAD_DIR / session_id
    work_dir.mkdir(exist_ok=True)

    try:
        # 保存文件
        saved_files = []
        for f in files:
            file_path = work_dir / f.filename
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(f.file, buffer)
            saved_files.append(str(file_path))

        # 调用分析引擎
        result = analyze_company(saved_files, company_name, industry)

        # 生成HTML报告
        report_filename = f"{company_name}_{session_id}.html"
        report_path = REPORT_DIR / report_filename

        generate_html_report(
            company_name=company_name,
            industry=industry,
            analysis_result=result,
            output_path=str(report_path)
        )

        # 生成PDF（使用专业PDF报告生成器）
        pdf_path = None
        if PDF_READY and cfg.report.pdf_enabled and report_path.exists():
            try:
                pdf_filename = f"{company_name}_{session_id}.pdf"
                pdf_path = REPORT_DIR / pdf_filename
                pdf_html_path = REPORT_DIR / f"_{company_name}_{session_id}_pdf.html"
                generate_professional_pdf(
                    company_name=company_name,
                    industry=industry,
                    analysis_result=result,
                    output_path=str(pdf_html_path),
                )
                with open(pdf_html_path, 'r', encoding='utf-8') as f:
                    pdf_html = f.read()
                with open(pdf_path, 'wb') as pdf_file:
                    pisa.CreatePDF(pdf_html, pdf_file, encoding='utf-8')
                if pdf_html_path.exists():
                    pdf_html_path.unlink()
            except Exception as pdf_err:
                print(f"PDF生成失败: {pdf_err}")
                import traceback
                traceback.print_exc()
                pdf_path = None

        return JSONResponse(content={
            "success": True,
            "report_url": f"/api/report/{report_filename}",
            "pdf_url": f"/api/report/{pdf_filename}" if pdf_path and pdf_path.exists() else None,
            "summary": {
                "company_name": company_name,
                "industry": industry,
                "total_score": result.get("total_score", 0),
                "grade": result.get("grade", "N/A"),
                "suggestion": result.get("suggestion", ""),
                "periods": result.get("periods", []),
                "dimension_scores": result.get("dimension_scores", {}),
            }
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")
    finally:
        # 清理临时文件
        shutil.rmtree(work_dir, ignore_errors=True)


# ─────────────────────────────────────────────
# 报告下载接口
# ─────────────────────────────────────────────

@app.get("/api/report/{filename}")
async def get_report(filename: str):
    """获取生成的报告文件"""
    report_path = REPORT_DIR / filename

    if not report_path.exists():
        raise HTTPException(status_code=404, detail="报告不存在或已过期")

    # 根据文件扩展名确定媒体类型
    if filename.endswith('.pdf'):
        media_type = "application/pdf"
    else:
        media_type = "text/html"

    return FileResponse(
        str(report_path),
        media_type=media_type,
        filename=filename
    )


# ─────────────────────────────────────────────
# 批量分析接口
# ─────────────────────────────────────────────

@app.post("/api/batch-analyze")
async def batch_analyze(
    company_name: str = Form(...),
    industry: str = Form(...),
    data_directory: str = Form(None)
):
    """
    批量分析：指定目录下的所有财务文件
    """
    if not data_directory:
        raise HTTPException(status_code=400, detail="请指定数据目录")

    if not os.path.isdir(data_directory):
        raise HTTPException(status_code=400, detail="目录不存在")

    try:
        result = analyze_company([data_directory], company_name, industry, mode="directory")

        report_filename = f"{company_name}_batch_{uuid.uuid4().hex[:8]}.html"
        report_path = REPORT_DIR / report_filename

        generate_html_report(
            company_name=company_name,
            industry=industry,
            analysis_result=result,
            output_path=str(report_path)
        )

        return JSONResponse(content={
            "success": True,
            "report_url": f"/api/report/{report_filename}",
            "summary": {
                "company_name": company_name,
                "industry": industry,
                "total_score": result.get("total_score", 0),
                "grade": result.get("grade", "N/A"),
                "suggestion": result.get("suggestion", ""),
            }
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"批量分析失败: {str(e)}")


# ─────────────────────────────────────────────
# 系统状态接口
# ─────────────────────────────────────────────

@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {
        "status": "healthy",
        "version": cfg.cache.version,
        "pdf_ready": PDF_READY,
    }


@app.get("/api/system/status")
async def system_status():
    """系统状态接口"""
    task_status = task_manager.get_pool_status()

    return {
        "status": "healthy",
        "version": cfg.cache.version,
        "pdf_ready": PDF_READY,
        "tasks": task_status,
        "config": cfg.to_dict(),
    }


# ─────────────────────────────────────────────
# 清理过期报告
# ─────────────────────────────────────────────

@app.post("/api/cleanup")
async def cleanup_reports(max_age_hours: int = 24):
    """清理超过指定时间的报告文件"""
    current_time = time.time()
    max_age_seconds = max_age_hours * 3600
    cleaned = 0

    for f in REPORT_DIR.glob("*.html"):
        if current_time - f.stat().st_mtime > max_age_seconds:
            f.unlink()
            cleaned += 1

    for f in REPORT_DIR.glob("*.pdf"):
        if current_time - f.stat().st_mtime > max_age_seconds:
            f.unlink()

    return {"cleaned": cleaned, "message": f"已清理 {cleaned} 个过期报告"}
