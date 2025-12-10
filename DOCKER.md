# Docker Deployment Guide

This comprehensive guide covers deploying the Meeting Video Chapter Tool using Docker for consistent, portable execution across different environments. Docker provides a complete runtime environment with all dependencies pre-installed, including ffmpeg and Python packages.

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [GPU Setup](#gpu-setup)
- [Configuration](#configuration)
- [Usage Examples](#usage-examples)
- [Deployment Scenarios](#deployment-scenarios)
- [Troubleshooting](#troubleshooting)
- [Performance Optimization](#performance-optimization)
- [Security Considerations](#security-considerations)

## Quick Start

### 1. Initial Setup
```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd meeting-video-chapter-tool

# Copy and configure environment file
cp .env.example .env
# Edit .env with your GEMINI_API_KEY (see Configuration section)

# Create required directories
mkdir -p videos output cache
```

### 2. Get Your API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and add it to your `.env` file:
   ```bash
   GEMINI_API_KEY=your_actual_api_key_here
   ```

### 3. Choose Your Deployment Method

**Option A: Use Pre-built Images (Recommended)**
```bash
# Configure to use GitHub Container Registry images
./use-ghcr-images.sh your_github_username
# On Windows: use-ghcr-images.bat your_github_username

# Edit .env.ghcr and add your GEMINI_API_KEY

# Process with CPU (works on any system)
docker compose --env-file .env.ghcr run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Process with GPU (NVIDIA GPUs only, 5-10x faster)
docker compose --env-file .env.ghcr run --rm meeting-video-tool-gpu python -m src.main /input/meeting.mkv
```

**Option B: Build Images Locally**
```bash
# Build the CPU image
docker-compose build meeting-video-tool-cpu

# Build GPU-enabled image (requires GPU setup - see below)
docker-compose build meeting-video-tool-gpu

# Process with locally built images
docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv
```

## Prerequisites

### System Requirements

**Minimum Requirements:**
- Docker Engine 20.10+ 
- Docker Compose 2.0+
- 4GB RAM (8GB+ recommended)
- 5GB free disk space for base installation
- 10GB+ additional space for model cache

**Recommended for Production:**
- 8GB+ RAM (12GB+ for GPU acceleration)
- SSD storage for model cache
- Multi-core CPU (4+ cores recommended)

### Operating System Support

**Supported Platforms:**
- Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+)
- Windows 10/11 with WSL2 and Docker Desktop
- macOS 10.15+ with Docker Desktop

**Note:** GPU acceleration is only available on Linux with NVIDIA GPUs.

### Docker Installation

If Docker is not installed on your system:

**Linux (Ubuntu/Debian):**
```bash
# Install Docker Engine
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
# Log out and back in for group changes to take effect

# Install Docker Compose
sudo apt-get update
sudo apt-get install docker-compose-plugin
```

**Windows/macOS:**
- Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- Ensure WSL2 is enabled on Windows

**Verify Installation:**
```bash
docker --version
docker compose version
```

## GPU Setup

GPU acceleration provides 5-10x faster transcription performance but requires additional setup.

### Prerequisites for GPU Support
- NVIDIA GPU with CUDA Compute Capability 6.0+ (GTX 1060 or newer)
- NVIDIA drivers 470.57.02+ (for CUDA 11.8) or 525.60.13+ (for CUDA 12.1)
- Linux operating system (GPU acceleration not available on Windows/macOS Docker)

### Installing NVIDIA Container Toolkit

**Ubuntu/Debian:**
```bash
# Add NVIDIA package repository
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install the toolkit
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

**RHEL/CentOS:**
```bash
# Add NVIDIA repository
curl -s -L https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo | \
  sudo tee /etc/yum.repos.d/nvidia-container-toolkit.repo

# Install the toolkit
sudo yum install -y nvidia-container-toolkit

# Configure and restart Docker
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

### Verify GPU Setup

**Test NVIDIA Container Toolkit:**
```bash
# This should show your GPU information
docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu20.04 nvidia-smi
```

**Test with the Meeting Video Tool:**
```bash
# Build GPU image
docker-compose build meeting-video-tool-gpu

# Test GPU detection
docker-compose run --rm meeting-video-tool-gpu python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'GPU count: {torch.cuda.device_count()}')"
```

### GPU Troubleshooting

**Common Issues:**

1. **"nvidia-smi not found" in container:**
   - Ensure NVIDIA drivers are installed on host
   - Verify `nvidia-container-toolkit` is installed and configured

2. **"CUDA out of memory" errors:**
   - Use smaller Whisper model: `WHISPER_MODEL=openai/whisper-medium`
   - Increase Docker memory limits in compose file

3. **GPU not detected by PyTorch:**
   - Check CUDA version compatibility
   - Verify container has GPU access: `docker run --rm --gpus all <image> nvidia-smi`

## Configuration

### Environment Variables

The Docker deployment supports comprehensive configuration through environment variables.

#### Required Configuration

Create a `.env` file from the example:
```bash
cp .env.example .env
```

**Essential Settings:**
```bash
# Required: Get your API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_actual_api_key_here
```

#### Optional Configuration

**Model Selection (affects accuracy vs speed vs memory):**
```bash
# Whisper model variants
WHISPER_MODEL=openai/whisper-large-v3-turbo  # Best accuracy, slower (default)
# WHISPER_MODEL=openai/whisper-medium        # Balanced performance
# WHISPER_MODEL=openai/whisper-base          # Fastest, lower accuracy

# Gemini model selection
GEMINI_MODEL=gemini-flash-latest             # Fast, good quality (default)
# GEMINI_MODEL=gemini-pro                    # Higher quality, slower
```

**Performance Optimization:**
```bash
# Skip regenerating files that already exist (great for batch processing)
SKIP_EXISTING=false

# Output directory (default: same as input file)
OUTPUT_DIR=./output

# Add chapter titles as video overlays
OVERLAY_CHAPTER_TITLES=false
```

**GPU Configuration (multi-GPU systems):**
```bash
# Select specific GPU (0, 1, 2, etc.)
CUDA_VISIBLE_DEVICES=0

# Memory management for large models
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024
```

### Volume Mounts and Data Management

The Docker setup uses three main volume mounts for data persistence and organization:

#### 1. Input Videos (`./videos:/input`)
- **Purpose**: Source video files for processing
- **Recommended**: Mount as read-only (`:ro`) for safety
- **Supported formats**: MKV files with audio tracks
- **Example**: Place `meeting.mkv` in `./videos/` directory

#### 2. Output Files (`./output:/output`)
- **Purpose**: Processed files and results
- **Contents**: Chaptered videos, transcripts, subtitles, notes
- **Permissions**: Must be writable by container
- **Structure**: Organized by input filename

#### 3. Model Cache (`./cache:/cache`)
- **Purpose**: Persistent storage for downloaded AI models
- **Benefits**: Avoids re-downloading models (saves time and bandwidth)
- **Size**: 2-5GB depending on models used
- **Recommendation**: Use fast SSD storage for better performance

#### Volume Configuration Examples

**Basic setup (recommended for most users):**
```yaml
volumes:
  - ./videos:/input:ro          # Read-only input
  - ./output:/output            # Writable output
  - ./cache:/cache              # Persistent model cache
```

**Co-located output (saves alongside input files):**
```yaml
volumes:
  - ./videos:/input             # Writable for co-located output
  - ./cache:/cache              # Model cache only
# Don't set OUTPUT_DIR environment variable
```

**Network storage setup:**
```yaml
volumes:
  - /mnt/nas/videos:/input:ro
  - /mnt/nas/processed:/output
  - /fast-ssd/cache:/cache      # Local SSD for model cache
```

## Usage Examples

### Basic Processing

**Process a single video file:**
```bash
# CPU processing
docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# GPU processing (5-10x faster)
docker-compose run --rm meeting-video-tool-gpu python -m src.main /input/meeting.mkv
```

**Windows-specific usage (Git Bash path translation fix):**
```bash
# Option 1: Use double slashes to prevent path translation
docker-compose run --rm meeting-video-tool-cpu python -m src.main //input/meeting.mkv

# Option 2: Use PowerShell or Command Prompt (recommended)
# PowerShell:
docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Option 3: Set environment variable in Git Bash
MSYS_NO_PATHCONV=1 docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Option 4: Use filename without leading slash
docker-compose run --rm meeting-video-tool-cpu python -m src.main "input/meeting.mkv"
```

**Process all videos in a directory:**
```bash
# Process all .mkv files in ./videos directory
docker-compose run --rm meeting-video-tool-cpu python -m src.main /input

# With GPU acceleration
docker-compose run --rm meeting-video-tool-gpu python -m src.main /input
```

### Advanced Configuration

**Use different Whisper models for speed/accuracy tradeoff:**
```bash
# Fast processing with base model (lower accuracy)
WHISPER_MODEL=openai/whisper-base docker-compose run --rm meeting-video-tool-cpu python -m src.main /input

# Balanced performance with medium model
WHISPER_MODEL=openai/whisper-medium docker-compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Batch processing with optimization:**
```bash
# Skip existing files to resume interrupted batch processing
SKIP_EXISTING=true docker-compose run --rm meeting-video-tool-cpu python -m src.main /input

# Process with chapter title overlays
OVERLAY_CHAPTER_TITLES=true docker-compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Custom output directory:**
```bash
# Specify custom output location
docker-compose run --rm \
  -e OUTPUT_DIR=/output/processed-$(date +%Y%m%d) \
  meeting-video-tool-cpu python -m src.main /input
```

### Production Workflows

**Automated batch processing:**
```bash
#!/bin/bash
# batch-process.sh - Process all videos with error handling

set -e

echo "Starting batch processing at $(date)"

# Set environment for production
export SKIP_EXISTING=true
export WHISPER_MODEL=openai/whisper-large-v3-turbo

# Process with GPU if available, fallback to CPU
if docker-compose run --rm meeting-video-tool-gpu python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    echo "Using GPU acceleration"
    docker-compose run --rm meeting-video-tool-gpu python -m src.main /input
else
    echo "Using CPU processing"
    docker-compose run --rm meeting-video-tool-cpu python -m src.main /input
fi

echo "Batch processing completed at $(date)"
```

**Scheduled processing with cron:**
```bash
# Add to crontab for daily processing at 2 AM
# crontab -e
0 2 * * * cd /path/to/meeting-video-tool && ./batch-process.sh >> /var/log/video-processing.log 2>&1
```

### Development and Testing

**Development mode with live code reloading:**
```bash
# CPU development (mounts source code for live editing)
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up meeting-video-tool-cpu

# GPU development
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up meeting-video-tool-gpu
```

**Interactive debugging:**
```bash
# Access container shell for debugging
docker-compose run --rm meeting-video-tool-cpu bash

# Run Python interactively
docker-compose run --rm meeting-video-tool-cpu python

# Test specific components
docker-compose run --rm meeting-video-tool-cpu python -c "
import torch
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
if torch.cuda.is_available():
    print(f'GPU count: {torch.cuda.device_count()}')
    print(f'Current GPU: {torch.cuda.current_device()}')
"
```

### Performance Testing

**Benchmark different configurations:**
```bash
# Test CPU performance
time docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/test-video.mkv

# Test GPU performance
time docker-compose run --rm meeting-video-tool-gpu python -m src.main /input/test-video.mkv

# Test different models
for model in base medium large-v3-turbo; do
    echo "Testing whisper-$model"
    time WHISPER_MODEL=openai/whisper-$model docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/test-video.mkv
done
```

## Service Configurations

### CPU Service (`meeting-video-tool-cpu`)
- **Base Image**: `python:3.12-slim` with CPU-optimized PyTorch
- **Memory Requirements**: 4-8GB (configurable)
- **CPU Requirements**: 2-4 cores recommended
- **Processing Speed**: ~30-60 minutes per hour of video
- **Use Cases**: 
  - Development and testing
  - Systems without NVIDIA GPU
  - Small-scale processing
  - Budget-conscious deployments

### GPU Service (`meeting-video-tool-gpu`)
- **Base Image**: `python:3.12-slim` with CUDA-enabled PyTorch
- **Memory Requirements**: 6-12GB (higher for large models)
- **GPU Requirements**: NVIDIA GPU with 4GB+ VRAM
- **Processing Speed**: ~5-10 minutes per hour of video
- **Use Cases**:
  - Production processing
  - Large file processing
  - Batch operations
  - Time-sensitive workflows

### Resource Allocation Guidelines

**For CPU Service:**
```yaml
deploy:
  resources:
    limits:
      memory: 8G        # Adjust based on available system memory
      cpus: '4.0'       # Adjust based on CPU cores
    reservations:
      memory: 4G        # Minimum required
      cpus: '2.0'       # Minimum required
```

**For GPU Service:**
```yaml
deploy:
  resources:
    limits:
      memory: 12G       # Higher for GPU processing
      cpus: '6.0'       # More CPU for GPU coordination
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
      memory: 6G
      cpus: '3.0'
```

## Deployment Scenarios

### 1. Development Environment

**Characteristics:**
- Local development with live code reloading
- Minimal resource allocation
- Easy debugging and testing

**Configuration:**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-cpu:
    volumes:
      - ./src:/app/src:ro          # Live code reloading
      - ./videos:/input:ro
      - ./output:/output
      - ./cache:/cache
    environment:
      - SKIP_EXISTING=true         # Speed up development
      - WHISPER_MODEL=openai/whisper-base  # Faster for testing
    command: ["tail", "-f", "/dev/null"]  # Keep container running
```

### 2. Co-located Output

**Characteristics:**
- Processed files saved alongside input videos
- Simplified file management
- Good for personal use

**Configuration:**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-cpu:
    volumes:
      - ./videos:/input            # Writable for co-located output
      - ./cache:/cache
    environment:
      # Don't set OUTPUT_DIR - defaults to input directory
      - SKIP_EXISTING=true
      - OVERLAY_CHAPTER_TITLES=true
```

### 3. Network Storage Deployment

**Characteristics:**
- Centralized storage for input and output
- Scalable for multiple users
- Separation of processing and storage

**Configuration:**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-cpu:
    volumes:
      - /mnt/nas/videos:/input:ro
      - /mnt/nas/processed:/output
      - /fast-ssd/cache:/cache     # Local SSD for performance
    environment:
      - OUTPUT_DIR=/output
      - SKIP_EXISTING=true
    networks:
      - storage_network

networks:
  storage_network:
    external: true
```

### 4. Production Deployment

**Characteristics:**
- High availability and reliability
- Resource limits and monitoring
- Automated restart and logging

**Configuration:**
```yaml
# docker-compose.override.yml
version: '3.8'
services:
  meeting-video-tool-cpu:
    restart: unless-stopped
    volumes:
      - /data/videos:/input:ro
      - /data/processed:/output
      - /cache/models:/cache
    environment:
      - OUTPUT_DIR=/output
      - SKIP_EXISTING=true
      - WHISPER_MODEL=openai/whisper-large-v3-turbo
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4.0'
        reservations:
          memory: 4G
          cpus: '2.0'
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
```

### 5. Multi-GPU Production Setup

**Characteristics:**
- Multiple GPU workers for high throughput
- Load balancing across GPUs
- Optimized for batch processing

**Configuration:**
```yaml
# docker-compose.override.yml
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
    
  # Load balancer (optional)
  nginx:
    image: nginx:alpine
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    ports:
      - "80:80"
    depends_on:
      - meeting-video-tool-gpu-0
      - meeting-video-tool-gpu-1
```

### 6. Cloud Deployment (AWS/GCP/Azure)

**Characteristics:**
- Scalable cloud infrastructure
- Managed storage and networking
- Auto-scaling capabilities

**AWS ECS Configuration:**
```yaml
# ecs-task-definition.json
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
        {"name": "GEMINI_API_KEY", "value": "${GEMINI_API_KEY}"},
        {"name": "OUTPUT_DIR", "value": "/output"}
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
      ]
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

## Troubleshooting

### Common Issues and Solutions

#### 1. Container Build Issues

**Problem: "Package not found" during build**
```bash
# Solution: Clear Docker build cache and rebuild
docker system prune -f
docker-compose build --no-cache meeting-video-tool-cpu
```

**Problem: "CUDA version mismatch"**
```bash
# Check your NVIDIA driver version
nvidia-smi

# Use compatible CUDA version in Dockerfile
# For driver 470+: Use CUDA 11.8
# For driver 525+: Use CUDA 12.1
```

#### 2. Runtime Configuration Issues

**Problem: "Missing required API key: GEMINI_API_KEY"**
```bash
# Verify .env file exists and contains the key
cat .env | grep GEMINI_API_KEY

# Check if environment variable is passed to container
docker-compose run --rm meeting-video-tool-cpu env | grep GEMINI
```

**Problem: "Permission denied" accessing files**
```bash
# Fix file permissions for Docker access
sudo chown -R $USER:$USER ./videos ./output ./cache
chmod -R 755 ./videos ./output ./cache

# On SELinux systems, add :Z flag to volumes
# volumes:
#   - ./videos:/input:ro,Z
```

#### 3. Performance and Memory Issues

**Problem: "Out of memory" errors**
```bash
# Use smaller Whisper model
WHISPER_MODEL=openai/whisper-base docker-compose run --rm meeting-video-tool-cpu python -m src.main /input

# Increase Docker memory limits (Docker Desktop)
# Settings > Resources > Memory > Increase limit

# For Linux, check available memory
free -h
```

**Problem: "Container killed (OOMKilled)"**
```bash
# Check Docker memory limits
docker stats

# Reduce memory usage in compose file
# deploy:
#   resources:
#     limits:
#       memory: 4G  # Reduce from 8G
```

#### 4. GPU-Specific Issues

**Problem: "CUDA out of memory"**
```bash
# Use smaller model or reduce batch size
WHISPER_MODEL=openai/whisper-medium docker-compose run --rm meeting-video-tool-gpu python -m src.main /input

# Check GPU memory usage
nvidia-smi

# Clear GPU memory cache
docker-compose run --rm meeting-video-tool-gpu python -c "import torch; torch.cuda.empty_cache()"
```

**Problem: "GPU not detected by PyTorch"**
```bash
# Verify GPU access in container
docker-compose run --rm meeting-video-tool-gpu nvidia-smi

# Check PyTorch CUDA support
docker-compose run --rm meeting-video-tool-gpu python -c "
import torch
print(f'CUDA available: {torch.cuda.is_available()}')
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA version: {torch.version.cuda}')
"

# Rebuild with correct CUDA version
docker-compose build --no-cache meeting-video-tool-gpu
```

#### 5. Model and Network Issues

**Problem: "Failed to download model"**
```bash
# Check internet connectivity
docker-compose run --rm meeting-video-tool-cpu ping -c 3 huggingface.co

# Clear model cache and retry
rm -rf ./cache/huggingface
docker-compose run --rm meeting-video-tool-cpu python -m src.main /input

# Use offline model if available
# Copy model files to ./cache/huggingface/models--openai--whisper-large-v3-turbo/
```

**Problem: "Gemini API rate limit exceeded"**
```bash
# Wait and retry (rate limits reset over time)
sleep 60

# Check API quota at https://makersuite.google.com/app/apikey
# Consider upgrading API plan for higher limits
```

#### 6. File Processing Issues

**Problem: "Input file not found" with Windows path translation**
```bash
# Issue: On Windows, /input/file.mkv becomes C:/Program Files/Git/input/file.mkv
# This happens in Git Bash, MSYS2, or similar shells

# Solution 1: Use double slashes to prevent path translation
docker-compose run --rm meeting-video-tool-cpu python -m src.main //input/meeting.mkv

# Solution 2: Use PowerShell or Command Prompt instead of Git Bash
# PowerShell:
docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Solution 3: Set MSYS_NO_PATHCONV environment variable in Git Bash
MSYS_NO_PATHCONV=1 docker-compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Solution 4: Use relative paths from container perspective
docker-compose run --rm meeting-video-tool-cpu python -m src.main input/meeting.mkv
```

**Problem: "No audio track found in video file"**
```bash
# Verify file has audio track
docker-compose run --rm meeting-video-tool-cpu ffmpeg -i /input/meeting.mkv

# Check file format and codec support
docker-compose run --rm meeting-video-tool-cpu ffprobe /input/meeting.mkv
```

**Problem: "Output files not created"**
```bash
# Check output directory permissions
ls -la ./output

# Verify container can write to output
docker-compose run --rm meeting-video-tool-cpu touch /output/test.txt

# Check for error messages in logs
docker-compose logs meeting-video-tool-cpu
```

### Debugging Tools and Commands

#### Container Inspection

**Access container shell for debugging:**
```bash
# CPU container
docker-compose run --rm meeting-video-tool-cpu bash

# GPU container with shell access
docker-compose run --rm meeting-video-tool-gpu bash

# Run specific commands in container
docker-compose run --rm meeting-video-tool-cpu python --version
docker-compose run --rm meeting-video-tool-cpu ffmpeg -version
```

**Check container configuration:**
```bash
# Inspect container configuration
docker-compose config

# View environment variables
docker-compose run --rm meeting-video-tool-cpu env

# Check mounted volumes
docker-compose run --rm meeting-video-tool-cpu df -h
```

#### Log Analysis

**View container logs:**
```bash
# Real-time logs from all services
docker-compose logs -f

# Logs from specific service
docker-compose logs meeting-video-tool-cpu

# Last 50 lines of logs
docker-compose logs --tail=50 meeting-video-tool-cpu
```

**Application-specific debugging:**
```bash
# Test Python imports
docker-compose run --rm meeting-video-tool-cpu python -c "
import sys
print('Python path:', sys.path)
try:
    import torch, transformers, google.generativeai
    print('All imports successful')
except ImportError as e:
    print('Import error:', e)
"

# Test ffmpeg functionality
docker-compose run --rm meeting-video-tool-cpu ffmpeg -f lavfi -i testsrc=duration=1:size=320x240:rate=1 -c:v libx264 /tmp/test.mp4
```

#### Resource Monitoring

**Monitor container resource usage:**
```bash
# Real-time resource monitoring
docker stats

# GPU usage monitoring (if available)
watch -n 1 nvidia-smi

# Disk usage in container
docker-compose run --rm meeting-video-tool-cpu du -sh /cache /input /output
```

#### Network Diagnostics

**Test network connectivity:**
```bash
# Test internet access
docker-compose run --rm meeting-video-tool-cpu ping -c 3 google.com

# Test API endpoints
docker-compose run --rm meeting-video-tool-cpu curl -s https://generativelanguage.googleapis.com/

# Test model download endpoints
docker-compose run --rm meeting-video-tool-cpu curl -s https://huggingface.co/
```

### Getting Additional Help

If issues persist after trying these solutions:

1. **Check the application logs** for specific error messages
2. **Verify system requirements** are met (RAM, disk space, GPU drivers)
3. **Test with a small sample file** to isolate the issue
4. **Review Docker and system logs** for underlying issues
5. **Update to the latest image** to get bug fixes and improvements

**Useful diagnostic information to collect:**
```bash
# System information
docker --version
docker-compose --version
nvidia-smi  # If using GPU

# Container information
docker-compose config
docker-compose ps
docker images | grep meeting-video-tool

# Resource usage
df -h
free -h
docker system df
```

## Performance Optimization

### Model Selection Strategy

Choose the right Whisper model based on your requirements:

| Model | Size | Speed | Accuracy | Use Case |
|-------|------|-------|----------|----------|
| `whisper-base` | ~39 MB | Fastest | Good | Development, testing, quick processing |
| `whisper-medium` | ~769 MB | Balanced | Better | Production with time constraints |
| `whisper-large-v3-turbo` | ~1550 MB | Slower | Best | Production requiring highest accuracy |

**Configuration examples:**
```bash
# Fast processing for development
WHISPER_MODEL=openai/whisper-base

# Balanced for most production use
WHISPER_MODEL=openai/whisper-medium

# Best quality for critical applications
WHISPER_MODEL=openai/whisper-large-v3-turbo
```

### Memory and Storage Optimization

**Model Caching:**
```bash
# Persistent cache to avoid re-downloading models
volumes:
  - ./cache:/cache

# Pre-download models to reduce first-run time
docker-compose run --rm meeting-video-tool-cpu python -c "
from transformers import WhisperProcessor, WhisperForConditionalGeneration
model = WhisperForConditionalGeneration.from_pretrained('openai/whisper-base')
print('Model cached successfully')
"
```

**Memory Management:**
```bash
# Optimize for limited memory systems
WHISPER_MODEL=openai/whisper-base
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# For systems with ample memory
deploy:
  resources:
    limits:
      memory: 16G
    reservations:
      memory: 8G
```

**Batch Processing Optimization:**
```bash
# Skip existing files for efficient batch processing
SKIP_EXISTING=true

# Process multiple files efficiently
for file in ./videos/*.mkv; do
    echo "Processing: $file"
    docker-compose run --rm meeting-video-tool-cpu python -m src.main "/input/$(basename "$file")"
done
```

### GPU Performance Tuning

**Single GPU Optimization:**
```bash
# Optimize GPU memory usage
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:1024

# Monitor GPU utilization
watch -n 1 'nvidia-smi --query-gpu=utilization.gpu,memory.used,memory.total --format=csv'
```

**Multi-GPU Setup:**
```bash
# Use specific GPU
CUDA_VISIBLE_DEVICES=0 docker-compose run --rm meeting-video-tool-gpu python -m src.main /input

# Parallel processing on multiple GPUs
for gpu in 0 1; do
    CUDA_VISIBLE_DEVICES=$gpu docker-compose run --rm -d meeting-video-tool-gpu python -m src.main /input/batch-$gpu &
done
wait
```

### Network and I/O Optimization

**Storage Performance:**
```bash
# Use SSD for model cache
volumes:
  - /fast-ssd/cache:/cache

# Separate input/output for better I/O
volumes:
  - /storage/input:/input:ro
  - /fast-storage/output:/output
```

**Network Optimization:**
```bash
# Pre-pull images to avoid download delays
docker-compose pull

# Use local registry for faster deployment
docker tag meeting-video-tool:cpu localhost:5000/meeting-video-tool:cpu
docker push localhost:5000/meeting-video-tool:cpu
```

## Security Considerations

### Container Security

**Non-root Execution:**
- Container runs as `appuser` (UID 10001) for security
- Application files owned by non-root user
- No sudo or privileged access required

**Minimal Attack Surface:**
```dockerfile
# Uses minimal base image
FROM python:3.12-slim

# Only installs required packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# No unnecessary services or ports
EXPOSE # No ports exposed by default
```

**File System Security:**
```yaml
# Read-only input volumes when possible
volumes:
  - ./videos:/input:ro

# Specific volume permissions
volumes:
  - ./output:/output:rw,Z  # SELinux context on RHEL/CentOS
```

### API Key Management

**Environment Variable Security:**
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

**Key Rotation:**
```bash
# Update API key without rebuilding
docker-compose down
# Update .env file with new key
docker-compose up -d
```

### Network Security

**Isolated Networks:**
```yaml
# Create isolated network for processing
networks:
  processing:
    driver: bridge
    internal: true  # No external access

services:
  meeting-video-tool-cpu:
    networks:
      - processing
      - default  # For API access
```

**Firewall Configuration:**
```bash
# Allow only necessary outbound connections
# Gemini API: generativelanguage.googleapis.com:443
# Hugging Face: huggingface.co:443
# PyTorch: download.pytorch.org:443
```

### Production Security Checklist

- [ ] Use non-root user in containers
- [ ] Mount input volumes as read-only
- [ ] Use Docker secrets for API keys
- [ ] Implement resource limits
- [ ] Enable container logging
- [ ] Regular base image updates
- [ ] Network segmentation
- [ ] File permission validation
- [ ] API key rotation procedures
- [ ] Security scanning of images

## Makefile Commands

The included Makefile provides convenient commands for common operations:

### Basic Commands
```bash
make help          # Show all available commands with descriptions
make setup         # Initial setup: create directories, copy .env.example
make clean         # Clean up containers, images, and volumes
```

### Build Commands
```bash
make build         # Build CPU-only image
make build-gpu     # Build GPU-enabled image
make build-all     # Build both CPU and GPU images
make rebuild       # Force rebuild without cache
```

### Processing Commands
```bash
make process       # Process videos using CPU
make process-gpu   # Process videos using GPU (requires GPU setup)
make process-fast  # Process using base model for speed
make batch         # Batch process all videos with optimization
```

### Development Commands
```bash
make dev           # Start development environment with live reloading
make dev-gpu       # Start GPU development environment
make shell         # Access container shell for debugging
make test          # Run application tests
```

### Monitoring Commands
```bash
make logs          # View container logs
make stats         # Show container resource usage
make check-gpu     # Test GPU support and configuration
make health        # Check system health and requirements
```

### Maintenance Commands
```bash
make update        # Pull latest base images and rebuild
make prune         # Clean up unused Docker resources
make backup-cache  # Backup model cache directory
make restore-cache # Restore model cache from backup
```

### Example Makefile Usage
```bash
# Complete setup and first run
make setup
# Edit .env file with your API key
make build
make process

# Development workflow
make dev
# Make code changes
make test
make process-fast  # Quick test with base model

# Production deployment
make build-all
make batch         # Process all videos efficiently
make logs          # Monitor processing
```

The Makefile simplifies Docker operations and provides consistent commands across different environments. All commands include error handling and helpful output messages.