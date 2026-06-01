@echo off
REM =============================================================================
REM 信贷风险分析系统 v3.0 - Windows 启动脚本
REM =============================================================================

echo ========================================
echo   信贷风险分析系统 v3.0 启动中...
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 检查虚拟环境
if not exist "venv\Scripts\python.exe" (
    echo.
    echo [1/4] 创建虚拟环境...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [2/4] 安装依赖...
    pip install -r requirements.txt
) else (
    echo.
    echo [1/4] 虚拟环境已存在，跳过创建
    call venv\Scripts\activate.bat
)

REM 创建目录
echo.
echo [3/4] 初始化目录...
if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports
if not exist "data" mkdir data

REM 启动服务
echo.
echo [4/4] 启动 FastAPI 服务...
echo.
echo   访问地址:  http://localhost:8000
echo   API 文档:  http://localhost:8000/docs
echo   健康检查:  http://localhost:8000/health
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
