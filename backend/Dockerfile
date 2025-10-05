FROM python:3.11-slim

# DEPRECATED: This Dockerfile is kept for backward compatibility only.
# For production deployments, use /Dockerfile.backend from the project root
# with build context set to project root.
#
# If you must use this file, it assumes the build context is the backend/ directory
# and will create a structure where backend becomes the package root.

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements from project root (one level up from backend/)
COPY ../requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend contents to /app/backend to maintain package structure
COPY . /app/backend

# Create necessary directories
RUN mkdir -p /app/logs /tmp/uploads

# Expose port
EXPOSE 8000

# Health check using the full package path
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run the application using full package path from project root
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]



