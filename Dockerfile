# Dockerfile for Jurisol: AI-Powered Indian Legal Assistant

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

# Copy requirements first for better caching
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Create directory for Chroma database
RUN mkdir -p /app/tools/chroma_legal_index

# Copy project files
COPY . .

# Expose ports for both FastAPI and Streamlit
EXPOSE 8501

# Create a non-root user for security
RUN useradd -r -u 999 -g users jurisol && \
    chown -R jurisol:users /app
USER jurisol

# Print SQLite version on startup for verification
RUN python -c "import sqlite3; print(f'SQLite version: {sqlite3.sqlite_version}')"

# Start both backend and frontend services
CMD ["sh", "-c", "streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0"]