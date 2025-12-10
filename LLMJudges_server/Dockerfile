# Use Python 3.12 slim image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    bash \
    && rm -rf /var/lib/apt/lists/* 
    

# Copy project files
COPY pyproject.toml /app/
COPY LLMJudges_server /app/LLMJudges_server

# Install uv for faster dependency management
RUN pip install uv

# Install Python dependencies
RUN uv pip install --system -e .

# Expose the application port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5000/llm-judges/health || exit 1

# Run the FastAPI application
# Development version with auto-reload
CMD ["uvicorn", "LLMJudges_server.src.main:app", "--host", "0.0.0.0", "--port", "5000", "--reload"]

