# Dockerfile for Jurisol: AI-Powered Indian Legal Assistant (Frontend Only)

# Use Python slim image for better package compatibility
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    python3-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create directory for Chroma database
RUN mkdir -p /app/tools/chroma_legal_index

# Copy files in specific order
COPY requirements.txt ./
COPY frontend.py ./
COPY app.py ./
COPY tools/ ./tools/

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Expose Streamlit port
EXPOSE 8501

# Create a non-root user for security
RUN useradd -r -u 999 -g users jurisol && \
    chown -R jurisol:users /app
USER jurisol

# Healthcheck for Streamlit
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Start Streamlit frontend
CMD ["streamlit", "run", "frontend.py", "--server.port", "8501", "--server.address", "0.0.0.0"]