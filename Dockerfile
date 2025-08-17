# Dockerfile for Jurisol: AI-Powered Indian Legal Assistant

# Use official Python image with slim variant for smaller size
FROM python:3.12-slim as builder

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies and build SQLite3 from source (Chroma requires >= 3.35.0)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and install latest SQLite
RUN wget https://www.sqlite.org/2024/sqlite-autoconf-3450000.tar.gz \
    && tar xzf sqlite-autoconf-3450000.tar.gz \
    && cd sqlite-autoconf-3450000 \
    && ./configure --prefix=/usr/local \
    && make \
    && make install \
    && cd .. \
    && rm -rf sqlite-autoconf-3450000*

# Update library path to use the new SQLite
ENV LD_LIBRARY_PATH=/usr/local/lib

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
EXPOSE 8000 8501

# Create a non-root user for security
RUN useradd -m -u 1000 jurisol && \
    chown -R jurisol:jurisol /app
USER jurisol

# Start both backend and frontend services
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port 8000 & streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0"]
