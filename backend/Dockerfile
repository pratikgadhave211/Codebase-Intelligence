FROM python:3.11-slim

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Limit ONNX/FastEmbed memory usage to prevent OOM kills on small servers
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV TOKENIZERS_PARALLELISM=false
WORKDIR /app

# System dependencies required by some Python packages
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Start FastAPI using dynamic PORT environment variable (default 8000)
# This is required for platforms like Railway and Render
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}