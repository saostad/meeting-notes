# Meeting Video Chapter Tool - Deployment Guide

This guide provides comprehensive instructions for deploying the Meeting Video Chapter Tool using Docker across different environments and use cases.

## Table of Contents

- [Quick Start](#quick-start)
- [Environment Setup](#environment-setup)
- [GPU Configuration](#gpu-configuration)
- [Deployment Scenarios](#deployment-scenarios)
- [Configuration Examples](#configuration-examples)
- [Troubleshooting](#troubleshooting)
- [Performance Tuning](#performance-tuning)
- [Security Best Practices](#security-best-practices)

## Quick Start

### 1. Prerequisites Check

Ensure your system meets the requirements:

```bash
# Check Docker installation
docker --version  # Should be 20.10+
docker compose version  # Should be 2.0+

# Check available resources
free -h  # Should have 4GB+ RAM available
df -h    # Should have 10GB+ free disk space

# For GPU support (optional)
nvidia-smi  # Should show GPU information
```

### 2. Initial Setup

```bash
# Clone and setup the project
git clone <repository-url>
cd meeting-video-chapter-tool

# Create required directories
mkdir -p videos output cache

# Copy and configure environment
cp .env.example .env
# Edit .env with your GEMINI_API_KEY
```

### 3. Get API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key to your `.env` file:
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   ```

### 4. First Run

```bash
# Build and test CPU version
docker compose build meeting-video-tool-cpu

# Place a test video in ./videos/test.mkv
# Process the test video
docker compose run --rm meeting-video-tool-cpu python -m src.main /input/test.mkv

# Check output in ./output/
ls -la output/
```

## Environment Setup

### Environment File Selection

Choose the appropriate environment file for your use case:

| File | Use Case | Model Speed | Resource Usage |
|------|----------|-------------|----------------|
| `.env.example` | General use | Balanced | Medium |
| `.env.development` | Development/Testing | Fast | Low |
| `.env.production` | Production deployment | High quality | High |
| `.env.docker` | Docker-optimized | Configurable | Medium |

### Configuration Examples

**Development Environment:**
```bash
# Use development settings
cp .env.development .env
# Edit GEMINI_API_KEY
docker compose build meeting-video-tool-cpu
```

**Production Environment:**
```bash
# Use production settings
cp .env.production .env
# Set GEMINI_API_KEY in your deployment system
export GEMINI_API_KEY=your_key_here
docker compose build meeting-video-tool-gpu
```

## GPU Configuration

### Prerequisites for GPU Support

1. **NVIDIA GPU Requirements:**
   - CUDA Compute Capability 6.0+ (GTX 1060 or newer)
   - 4GB+ VRAM (8GB+ recommended)
   - Linux operating system

2. **Driver Requirements:**
   - NVIDIA drivers 470.57.02+ (for CUDA 11.8)
   - NVIDIA drivers 525.60.13+ (for CUDA 12.1)

### GPU Setup Steps

#### Step 1: Install NVIDIA Container Toolkit

**Ubuntu/Debian:**
```bash
# Add NVIDIA package repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**RHEL/CentOS/Fedora:**
```bash
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

sudo yum install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

#### Step 2: Verify GPU Setup

```bash
# Test NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu20.04 nvidia-smi

# Build GPU-enabled image
docker compose build meeting-video-tool-gpu

# Test GPU detection in application
docker compose run --rm meeting-video-tool-gpu python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'GPU count: {torch.cuda.device_count()}')
if torch.cuda.is_available():
    print(f'GPU name: {torch.cuda.get_device_name(0)}')
    print(f'GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
"
```

#### Step 3: GPU Performance Testing

```bash
# Test processing speed comparison
echo "Testing CPU performance..."
time docker compose run --rm meeting-video-tool-cpu python -m src.main /input/test.mkv

echo "Testing GPU performance..."
time docker compose run --rm meeting-video-tool-gpu python -m src.main /input/test.mkv
```

### GPU Troubleshooting

**Issue: "nvidia-smi not found"**
```bash
# Check NVIDIA drivers on host
nvidia-smi

# If not found, install drivers
sudo apt-get install nvidia-driver-525  # Ubuntu
# OR
sudo yum install nvidia-driver  # RHEL/CentOS
```

**Issue: "CUDA out of memory"**
```bash
# Use smaller model
WHISPER_MODEL=openai/whisper-medium docker compose run --rm meeting-video-tool-gpu python -m src.main /input

# Check GPU memory usage
nvidia-smi

# Adjust memory allocation
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 docker compose run --rm meeting-video-tool-gpu python -m src.main /input
```

## Deployment Scenarios

### Scenario 1: Personal Desktop

**Characteristics:**
- Single user
- Local file processing
- Mixed CPU/GPU usage

**Setup:**
```bash
# Use co-located output for simplicity
cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  meeting-video-tool-cpu:
    volumes:
      - ./videos:/input
      - ./cache:/cache
    environment:
      - SKIP_EXISTING=true
      - OVERLAY_CHAPTER_TITLES=true
EOF

# Process videos
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

### Scenario 2: Team Server

**Characteristics:**
- Multiple users
- Shared storage
- Batch processing

**Setup:**
```bash
# Create shared directories
sudo mkdir -p /shared/videos /shared/processed /shared/cache
sudo chown -R $USER:$USER /shared

# Configure for shared use
cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  meeting-video-tool-cpu:
    volumes:
      - /shared/videos:/input:ro
      - /shared/processed:/output
      - /shared/cache:/cache
    environment:
      - OUTPUT_DIR=/output
      - SKIP_EXISTING=true
    restart: unless-stopped
EOF

# Setup batch processing script
cat > batch-process.sh << 'EOF'
#!/bin/bash
set -e
echo "Starting batch processing at $(date)"
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
echo "Batch processing completed at $(date)"
EOF

chmod +x batch-process.sh

# Schedule with cron (daily at 2 AM)
echo "0 2 * * * cd $(pwd) && ./batch-process.sh >> /var/log/video-processing.log 2>&1" | crontab -
```

### Scenario 3: Cloud Deployment

**Characteristics:**
- Scalable infrastructure
- Auto-scaling
- High availability

**AWS ECS Setup:**
```json
{
  "family": "meeting-video-tool",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "2048",
  "memory": "8192",
  "containerDefinitions": [
    {
      "name": "meeting-video-tool",
      "image": "your-registry/meeting-video-tool:cpu",
      "environment": [
        {"name": "GEMINI_API_KEY", "valueFrom": "arn:aws:ssm:region:account:parameter/gemini-api-key"},
        {"name": "OUTPUT_DIR", "value": "/output"},
        {"name": "SKIP_EXISTING", "value": "true"}
      ],
      "mountPoints": [
        {
          "sourceVolume": "efs-storage",
          "containerPath": "/input",
          "readOnly": true
        },
        {
          "sourceVolume": "efs-storage", 
          "containerPath": "/output",
          "readOnly": false
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/meeting-video-tool",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ],
  "volumes": [
    {
      "name": "efs-storage",
      "efsVolumeConfiguration": {
        "fileSystemId": "fs-12345678"
      }
    }
  ]
}
```

### Scenario 4: High-Performance GPU Cluster

**Characteristics:**
- Multiple GPUs
- Parallel processing
- Maximum throughput

**Setup:**
```bash
# Multi-GPU configuration
cat > docker-compose.override.yml << EOF
version: '3.8'
services:
  meeting-video-tool-gpu-0:
    extends:
      service: meeting-video-tool-gpu
    environment:
      - CUDA_VISIBLE_DEVICES=0
    container_name: video-tool-gpu-0
    
  meeting-video-tool-gpu-1:
    extends:
      service: meeting-video-tool-gpu
    environment:
      - CUDA_VISIBLE_DEVICES=1
    container_name: video-tool-gpu-1
    
  meeting-video-tool-gpu-2:
    extends:
      service: meeting-video-tool-gpu
    environment:
      - CUDA_VISIBLE_DEVICES=2
    container_name: video-tool-gpu-2
    
  meeting-video-tool-gpu-3:
    extends:
      service: meeting-video-tool-gpu
    environment:
      - CUDA_VISIBLE_DEVICES=3
    container_name: video-tool-gpu-3
EOF

# Parallel processing script
cat > parallel-process.sh << 'EOF'
#!/bin/bash
set -e

# Split videos across GPUs
videos=(./videos/*.mkv)
gpu_count=4

for i in "${!videos[@]}"; do
    gpu=$((i % gpu_count))
    video="${videos[$i]}"
    echo "Processing $video on GPU $gpu"
    
    CUDA_VISIBLE_DEVICES=$gpu docker compose run --rm -d \
        meeting-video-tool-gpu-$gpu \
        python -m src.main "/input/$(basename "$video")" &
done

# Wait for all processes to complete
wait
echo "All processing completed"
EOF

chmod +x parallel-process.sh
```

## Configuration Examples

### Basic Configuration

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-cpu:
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - WHISPER_MODEL=openai/whisper-medium
      - SKIP_EXISTING=true
```

### Performance-Optimized Configuration

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-gpu:
    environment:
      - WHISPER_MODEL=openai/whisper-large-v3-turbo
      - PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048
      - SKIP_EXISTING=true
    deploy:
      resources:
        limits:
          memory: 16G
          cpus: '8.0'
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Production Configuration with Monitoring

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-cpu:
    restart: unless-stopped
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LOG_LEVEL=INFO
      - SKIP_EXISTING=true
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    healthcheck:
      test: ["CMD", "python", "-c", "import src.main; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
      
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

## Performance Tuning

### Model Selection Guidelines

| Video Length | Recommended Model | Expected Processing Time |
|--------------|-------------------|-------------------------|
| < 30 minutes | whisper-base | 2-5 minutes (CPU), 30s-1min (GPU) |
| 30-60 minutes | whisper-medium | 5-15 minutes (CPU), 1-3 minutes (GPU) |
| > 60 minutes | whisper-large-v3-turbo | 15-60 minutes (CPU), 3-10 minutes (GPU) |

### Memory Optimization

```bash
# For systems with limited RAM (< 8GB)
WHISPER_MODEL=openai/whisper-base
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:256

# For systems with ample RAM (16GB+)
WHISPER_MODEL=openai/whisper-large-v3-turbo
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048
```

### Storage Optimization

```bash
# Use SSD for model cache
volumes:
  - /fast-ssd/cache:/cache

# Separate input/output storage
volumes:
  - /slow-storage/input:/input:ro
  - /fast-storage/output:/output
```

### Batch Processing Optimization

```bash
# Efficient batch processing
SKIP_EXISTING=true
WHISPER_MODEL=openai/whisper-medium

# Process in parallel (adjust based on resources)
for file in ./videos/*.mkv; do
    if [ $(jobs -r | wc -l) -ge 2 ]; then
        wait -n  # Wait for one job to finish
    fi
    docker compose run --rm meeting-video-tool-cpu python -m src.main "/input/$(basename "$file")" &
done
wait
```

## Security Best Practices

### API Key Security

```bash
# Use Docker secrets in production
echo "your_api_key" | docker secret create gemini_api_key -

# Reference in compose file
services:
  meeting-video-tool-cpu:
    secrets:
      - gemini_api_key
    environment:
      - GEMINI_API_KEY_FILE=/run/secrets/gemini_api_key
```

### File System Security

```bash
# Set proper permissions
sudo chown -R 10001:10001 ./cache ./output
chmod -R 755 ./cache ./output
chmod -R 644 ./videos  # Read-only input

# Use read-only volumes when possible
volumes:
  - ./videos:/input:ro,Z  # SELinux context
```

### Network Security

```yaml
# Isolated network for processing
networks:
  processing:
    driver: bridge
    internal: true

services:
  meeting-video-tool-cpu:
    networks:
      - processing
      - default  # For API access only
```

### Container Security

```yaml
# Security-hardened configuration
services:
  meeting-video-tool-cpu:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=1g
    cap_drop:
      - ALL
    cap_add:
      - CHOWN
      - SETUID
      - SETGID
```

## Troubleshooting

### Common Issues

**Issue: Container fails to start**
```bash
# Check logs
docker compose logs meeting-video-tool-cpu

# Verify configuration
docker compose config

# Test with minimal configuration
docker compose run --rm meeting-video-tool-cpu python --version
```

**Issue: API key not working**
```bash
# Verify API key is set
docker compose run --rm meeting-video-tool-cpu env | grep GEMINI

# Test API key manually
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=YOUR_API_KEY"
```

**Issue: Out of memory errors**
```bash
# Check available memory
free -h

# Use smaller model
WHISPER_MODEL=openai/whisper-base docker compose run --rm meeting-video-tool-cpu python -m src.main /input

# Increase Docker memory limits (Docker Desktop)
# Settings > Resources > Memory
```

**Issue: GPU not detected**
```bash
# Verify GPU setup
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu20.04 nvidia-smi

# Check container GPU access
docker compose run --rm meeting-video-tool-gpu nvidia-smi

# Verify PyTorch CUDA support
docker compose run --rm meeting-video-tool-gpu python -c "import torch; print(torch.cuda.is_available())"
```

### Performance Issues

**Issue: Slow processing**
```bash
# Use GPU if available
docker compose run --rm meeting-video-tool-gpu python -m src.main /input

# Use faster model
WHISPER_MODEL=openai/whisper-base docker compose run --rm meeting-video-tool-cpu python -m src.main /input

# Enable skip existing
SKIP_EXISTING=true docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Issue: High memory usage**
```bash
# Monitor memory usage
docker stats

# Reduce memory allocation
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 docker compose run --rm meeting-video-tool-gpu python -m src.main /input

# Use smaller model
WHISPER_MODEL=openai/whisper-medium docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

### Getting Help

For additional support:

1. Check the [main README](README.md) for general usage
2. Review [DOCKER.md](DOCKER.md) for detailed Docker information
3. Check container logs: `docker compose logs`
4. Verify system requirements and dependencies
5. Test with a small sample file first

**Diagnostic Information Collection:**
```bash
# System information
docker --version
docker compose version
nvidia-smi  # If using GPU

# Container information
docker compose config
docker compose ps
docker images | grep meeting-video-tool

# Resource usage
df -h
free -h
docker system df
```