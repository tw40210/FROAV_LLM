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
COPY LLMJudges_frontend /app/LLMJudges_frontend

# Install uv for faster dependency management
RUN pip install uv

# Install Python dependencies
RUN uv pip install --system -e .

# Expose the application port
EXPOSE 8501


# Run the Streamlit application
# Development version with auto-reload
CMD ["python", "-m", "streamlit", "run", "LLMJudges_frontend/src/main_page.py", "--server.port", "8501"]
# CMD ["tail", "-f", "/dev/null"]
