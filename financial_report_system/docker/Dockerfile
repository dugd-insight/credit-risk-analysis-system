# =============================================================================
# 信贷风险分析系统 v3.0 - Dockerfile
# =============================================================================
# 多阶段构建：减小最终镜像体积
# =============================================================================

# ── 构建阶段 ──
FROM python:3.11-slim AS builder

WORKDIR /build

# 安装编译依赖（仅构建阶段需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── 运行阶段 ──
FROM python:3.11-slim AS runtime

LABEL maintainer="dugd-insight"
LABEL description="信贷风险分析系统 v3.0 - 企业信用风险评估平台"
LABEL version="3.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    PATH="/install/bin:${PATH}"

WORKDIR /app

# 安装运行时系统依赖（中文字体支持 PDF 生成）
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/* \
    && fc-cache -f -v

# 从构建阶段复制 Python 包
COPY --from=builder /install /usr/local

# 复制应用代码
COPY app/ ./app/
COPY risk_engine/ ./risk_engine/

# 复制配置模板
COPY .env.example ./.env

# 创建必要目录（运行时由 volume 挂载覆盖）
RUN mkdir -p /app/uploads /app/reports /app/data /app/static

# 数据目录放置示例说明
RUN echo "将企业财务报表文件（.xls/.xlsx）放入此目录" > /app/data/README.txt

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
