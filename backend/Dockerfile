FROM python:3.10-slim

WORKDIR /app

# Install system dependencies (e.g., git, libmagic, build tools if needed)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code files
COPY backend/ ./backend/
COPY database/ ./database/

# Set PYTHONPATH environment variable to allow module resolution
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
