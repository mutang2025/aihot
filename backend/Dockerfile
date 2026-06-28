FROM python:3.11-slim

WORKDIR /app

# 系统依赖（编译 lxml/asyncpg 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Python 依赖
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

# 代码
COPY . .

# 数据目录
RUN mkdir -p /app/data/scraper_cache /app/data/embeddings /app/data/logs

EXPOSE 8000

# 默认启动 API；workers 用其他命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
