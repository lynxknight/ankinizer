# Use Python 3.11.11 as base image
FROM --platform=linux/arm64/v8 python:3.11.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Dependencies for Playwright
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user first
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Copy and install requirements first to leverage Docker cache
COPY build/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers as the non-root user
ENV PLAYWRIGHT_BROWSERS_PATH=/home/appuser/.cache/ms-playwright
RUN python -m playwright install chromium

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Copy application code (this should be the last step to leverage Docker cache)
COPY src/ /app/src/

RUN mkdir debug/

# Command to run the application
CMD ["python", "src/tgram.py"] 
