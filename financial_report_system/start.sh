#!/bin/bash
# =============================================================================
# 信贷风险分析系统 - Linux/Mac 启动脚本
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  信贷风险分析系统 v2.1.2${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Python 版本: $PYTHON_VERSION${NC}"

# 创建必要的目录
mkdir -p uploads reports data static

# 检查依赖
if ! pip3 show fastapi > /dev/null 2>&1; then
    echo -e "${YELLOW}正在安装依赖...${NC}"
    pip3 install -r requirements.txt
fi

# 启动服务
echo -e "${GREEN}启动服务...${NC}"
echo -e "${YELLOW}访问地址: http://localhost:8000${NC}"
echo -e "${YELLOW}按 Ctrl+C 停止服务${NC}"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
