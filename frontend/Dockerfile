FROM python:3.10-slim

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code files (including backend utilities for duration helpers)
COPY frontend/ ./frontend/
COPY backend/ ./backend/
COPY database/ ./database/
COPY .streamlit/ ./.streamlit/

# Set PYTHONPATH environment variable to allow module resolution
ENV PYTHONPATH=/app

EXPOSE 8501

CMD ["streamlit", "run", "frontend/app.py", "--server.port", "8501", "--server.address", "0.0.0.0"]
