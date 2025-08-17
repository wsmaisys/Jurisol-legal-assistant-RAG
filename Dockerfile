# Dockerfile for Jurisol: AI-Powered Indian Legal Assistant

# Use Python Alpine image for newer SQLite
FROM python:3.12-alpine

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apk add --no-cache \
    build-base \
    linux-headers \
    python3-dev \
    libffi-dev \
    openssl-dev \
    sqlite-dev

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
RUN adduser -D jurisol && \
    chown -R jurisol:jurisol /app
USER jurisol

# Start both backend and frontend services
CMD ["sh", "-c", "uvicorn app:app --host 0.0.0.0 --port 8000 & streamlit run frontend.py --server.port 8501 --server.address 0.0.0.0"]