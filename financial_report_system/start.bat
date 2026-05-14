@echo off
REM =============================================================================
REM 信贷风险分析系统 - Windows 启动脚本
REM =============================================================================

echo ========================================
echo   信贷风险分析系统启动中...
echo ========================================

REM 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到 Python，请先安装 Python 3.11+
    pause
    exit /b 1
)

REM 安装依赖
echo.
echo [1/3] 安装依赖...
pip install -r requirements.txt

REM 创建目录
echo.
echo [2/3] 初始化目录...
if not exist "uploads" mkdir uploads
if not exist "reports" mkdir reports
if not exist "data" mkdir data

REM 启动服务
echo.
echo [3/3] 启动 FastAPI 服务...
echo 访问地址: http://localhost:8000
echo API 文档: http://localhost:8000/docs
echo.

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

pause
