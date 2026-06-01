#!/bin/bash
# =============================================================================
# 信贷风险分析系统 v3.0 - Linux/Mac 启动脚本
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  信贷风险分析系统 v3.0${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Python 版本
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python3，请先安装 Python 3.11+${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo -e "${YELLOW}Python 版本: $PYTHON_VERSION${NC}"

# 检查/创建虚拟环境
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}[1/4] 创建虚拟环境...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${YELLOW}[2/4] 安装依赖...${NC}"
    pip install -r requirements.txt
else
    echo -e "${YELLOW}[1/4] 虚拟环境已存在${NC}"
    source venv/bin/activate
fi

# 创建必要目录
echo -e "${YELLOW}[3/4] 初始化目录...${NC}"
mkdir -p uploads reports data static

# 启动服务
echo -e "${YELLOW}[4/4] 启动服务...${NC}"
echo ""
echo -e "${GREEN}  访问地址:  http://localhost:8000${NC}"
echo -e "${GREEN}  API 文档:  http://localhost:8000/docs${NC}"
echo -e "${GREEN}  健康检查:  http://localhost:8000/health${NC}"
echo ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
