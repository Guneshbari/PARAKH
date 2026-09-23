FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies (including libgomp1 for LightGBM OpenMP support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY backend/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application code and Alembic migrations
COPY backend/alembic.ini .
COPY backend/alembic ./alembic
COPY backend/app ./app
COPY backend/docker-entrypoint.sh .
RUN chmod +x docker-entrypoint.sh

# Copy ML pipeline, model artifacts, and canonical dataset for inference
COPY src ./src
COPY models ./models
COPY data ./data

# Expose application port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=5s --timeout=3s --retries=10 --start-period=5s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

ENTRYPOINT ["./docker-entrypoint.sh"]

