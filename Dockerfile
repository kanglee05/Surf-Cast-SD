# Use a modern, supported Python (not 3.9) — the container gets its own,
# independent of what's on your Mac.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y libeccodes-dev && rm -rf /var/lib/apt/lists/*

# Don't write .pyc files; flush logs immediately so Cloud Run shows them live.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first (layer caching: deps rarely change, code does).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code.
COPY etl/ ./etl/
COPY scripts/ ./scripts/

# Run the forecast ETL as a module.
CMD ["python", "-m", "scripts.fetch_forecast"]
