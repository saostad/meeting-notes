# Minimal Docker image for Meeting Video Chapter Tool
# Downloads dependencies at runtime for fresh installs and small image size
FROM python:3.12-slim

# Install essential system dependencies and Ollama
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && curl -fsSL https://ollama.com/install.sh | sh

# Set working directory
WORKDIR /app

# Copy application code and setup script
COPY src/ ./src/
COPY requirements.txt ./
COPY setup.sh ./

# Make setup script executable
RUN chmod +x setup.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_MODELS=/workspace/models/ollama

# Use setup script as entrypoint for runtime dependency management
ENTRYPOINT ["./setup.sh"]