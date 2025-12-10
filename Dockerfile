# Multi-stage Docker build for Meeting Video Chapter Tool
# Stage 1: Build stage with all dependencies
FROM python:3.12-slim AS builder

# Install system dependencies and build tools
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    pkg-config \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    # Additional cleanup for image size optimization (Requirement 2.3)
    && rm -rf /var/cache/apt/* /tmp/* /var/tmp/*

# Create virtual environment for dependency isolation
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt /tmp/requirements.txt

# Install Python dependencies with caching
# Support both CPU and GPU PyTorch installations via build argument
ARG PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir torch torchvision torchaudio --index-url ${PYTORCH_INDEX_URL} && \
    pip install --no-cache-dir -r /tmp/requirements.txt && \
    # Cleanup pip cache and temporary files for image size optimization (Requirement 2.3)
    pip cache purge && \
    rm -rf /tmp/* /var/tmp/* /root/.cache

# Stage 2: Runtime stage with minimal footprint
FROM python:3.12-slim AS runtime

# Support GPU runtime via build argument
ARG ENABLE_GPU=false

# Install runtime system dependencies
# Add CUDA runtime libraries if GPU support is enabled
RUN apt-get update && apt-get install -y \
    ffmpeg \
    bash \
    wget \
    gnupg2 \
    && if [ "$ENABLE_GPU" = "true" ]; then \
        # Add NVIDIA package repository (modern approach without apt-key)
        wget -qO - https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/3bf863cc.pub | gpg --dearmor -o /usr/share/keyrings/nvidia-cuda-keyring.gpg && \
        echo "deb [signed-by=/usr/share/keyrings/nvidia-cuda-keyring.gpg] https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64 /" > /etc/apt/sources.list.d/cuda.list && \
        apt-get update && \
        # Install CUDA runtime (minimal for inference)
        apt-get install -y cuda-runtime-12-1 libcudnn8; \
    fi \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    # Additional cleanup for image size optimization (Requirement 2.3)
    && rm -rf /var/cache/apt/* /tmp/* /var/tmp/*

# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -u 10001 appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code and entrypoint script
COPY src/ ./src/
COPY fonts/ ./fonts/
COPY .env.example ./.env.example
COPY entrypoint.sh ./entrypoint.sh

# Make entrypoint script executable
RUN chmod +x ./entrypoint.sh

# Set appropriate file permissions for application user
RUN chown -R appuser:appuser /app

# Create directories for volumes with proper permissions (Requirements 4.3, 5.1, 5.2)
# Configure model cache directory for persistent model storage (Requirement 7.5)
RUN mkdir -p /input /output /cache /cache/huggingface /cache/models && \
    chown -R appuser:appuser /input /output /cache && \
    chmod 755 /input /output /cache

# Switch to non-root user
USER appuser

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Configure model caching for performance optimization (Requirement 7.5)
ENV HF_HOME=/cache/huggingface
ENV TRANSFORMERS_CACHE=/cache/huggingface
ENV HF_DATASETS_CACHE=/cache/huggingface/datasets
ENV TORCH_HOME=/cache/models

# Use entrypoint script for initialization and validation
ENTRYPOINT ["./entrypoint.sh"]
CMD ["python", "-m", "src.main", "--help"]