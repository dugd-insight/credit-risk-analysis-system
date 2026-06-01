# =============================================================================
# 信贷风险分析系统 v3.0 - 顶层 Dockerfile（便捷入口）
# 实际构建逻辑在 docker/Dockerfile，此文件用于根目录直接 docker build
# =============================================================================

FROM python:3.11-slim AS builder
WORKDIR /build
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.11-slim AS runtime
LABEL maintainer="dugd-insight" description="信贷风险分析系统 v3.0" version="3.0"
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TZ=Asia/Shanghai PATH="/install/bin:${PATH}"
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl fonts-wqy-microhei fonts-wqy-zenhei \
    && rm -rf /var/lib/apt/lists/* && fc-cache -f -v
COPY --from=builder /install /usr/local
COPY app/ ./app/
COPY risk_engine/ ./risk_engine/
COPY .env.example ./.env
RUN mkdir -p /app/uploads /app/reports /app/data /app/static
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
