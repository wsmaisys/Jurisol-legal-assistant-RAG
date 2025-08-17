# Dockerfile for Jurisol: AI-Powered Indian Legal Assistant

# Use official Python image with slim variant for smaller size
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    LD_LIBRARY_PATH=/usr/local/lib

# Set work directory
WORKDIR /app

# Install system dependencies for SQLite
RUN apt-get update && apt-get install -y \
    build-essential \
    libsqlite3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt ./

# Ensure pip is up-to-date and install dependencies
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir pysqlite3-binary && \
    pip install --no-cache-dir -r requirements.txt

# Configure Python to use pysqlite3
RUN echo 'import sys, pysqlite3; sys.modules["sqlite3"] = pysqlite3' > /usr/local/lib/python3.12/sqlite3_config.py && \
    echo 'import sqlite3_config' >> /usr/local/lib/python3.12/sitecustomize.py

# Create directory for Chroma database
RUN mkdir -p /app/tools/chroma_legal_index

# Copy project files
COPY . .

# Expose ports for both FastAPI and Streamlit
EXPOSE 8000 8501

# Create a non-root user for security
RUN useradd -m -u 1000 jurisol && \
    chown -R jurisol:jurisol /app
USER jurisol

# Start both backend and frontend services
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port 8000 & streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0"]