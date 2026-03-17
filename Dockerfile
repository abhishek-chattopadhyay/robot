FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/packages \
    PBPK_DATA_ROOT=/app/var

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

# Copy dependency metadata first for better layer caching
COPY pyproject.toml* uv.lock* ./

# Install dependencies
RUN sh -c 'if [ -f uv.lock ]; then uv sync --frozen --no-dev; else uv sync --no-dev; fi'

# Copy application source
COPY . .

# Ensure runtime directories exist
RUN mkdir -p /app/var/drafts /app/var/crates /app/var/logs

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "pbpk_backend.app:app", "--host", "0.0.0.0", "--port", "8000"]