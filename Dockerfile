# WebRTC Ops Environment — Standalone Dockerfile
# Lightweight: just Python + FastAPI + Pydantic (no real WebRTC stack)

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY server/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire environment package
COPY . /app/webrtc_ops_env

# Install the package itself
RUN pip install --no-cache-dir -e /app/webrtc_ops_env

# Set PYTHONPATH so imports work
ENV PYTHONPATH="/app"

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Run the FastAPI server
CMD ["uvicorn", "webrtc_ops_env.server.app:app", "--host", "0.0.0.0", "--port", "8000"]
