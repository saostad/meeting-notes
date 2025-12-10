# Docker Usage Examples

This document provides practical examples for using the Meeting Video Chapter Tool with Docker in various scenarios.

## Table of Contents

- [Basic Usage Examples](#basic-usage-examples)
- [Configuration Examples](#configuration-examples)
- [Batch Processing Examples](#batch-processing-examples)
- [Development Examples](#development-examples)
- [Production Examples](#production-examples)
- [Troubleshooting Examples](#troubleshooting-examples)

## Basic Usage Examples

### Single File Processing

**Process one video file with CPU:**
```bash
# Place video in ./videos/meeting.mkv
docker compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Output files will be in ./output/
ls -la output/
# meeting.mp3
# meeting_transcript.json
# meeting_notes.json
# meeting_chaptered.mkv
# meeting_chaptered.srt
```

**Windows-specific processing (fixes path translation issues):**
```bash
# If using Git Bash on Windows, use one of these methods:

# Method 1: Use double slashes (recommended for Git Bash)
docker compose run --rm meeting-video-tool-cpu python -m src.main //input/meeting.mkv

# Method 2: Use PowerShell or Command Prompt (most reliable)
# PowerShell:
docker compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Method 3: Disable path conversion in Git Bash
MSYS_NO_PATHCONV=1 docker compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Method 4: Use relative path without leading slash
docker compose run --rm meeting-video-tool-cpu python -m src.main "input/meeting.mkv"
```

**Process with GPU acceleration:**
```bash
# Requires GPU setup (see DEPLOYMENT.md)
docker compose run --rm meeting-video-tool-gpu python -m src.main /input/meeting.mkv
```

### Directory Processing

**Process all videos in a directory:**
```bash
# Process all .mkv files in ./videos/
docker compose run --rm meeting-video-tool-cpu python -m src.main /input

# With GPU
docker compose run --rm meeting-video-tool-gpu python -m src.main /input
```

### Custom Output Directory

**Specify where to save processed files:**
```bash
# Create custom output directory
mkdir -p ./processed/$(date +%Y%m%d)

# Process with custom output
docker compose run --rm \
  -e OUTPUT_DIR=/output/$(date +%Y%m%d) \
  meeting-video-tool-cpu \
  python -m src.main /input/meeting.mkv
```

## Configuration Examples

### Model Selection Examples

**Fast processing with base model:**
```bash
# Fastest processing, lower accuracy
WHISPER_MODEL=openai/whisper-base \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Balanced performance with medium model:**
```bash
# Good balance of speed and accuracy
WHISPER_MODEL=openai/whisper-medium \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Best quality with large model:**
```bash
# Best accuracy, slower processing
WHISPER_MODEL=openai/whisper-large-v3-turbo \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

### Environment Variable Examples

**Skip existing files (useful for resuming):**
```bash
# Skip files that already exist
SKIP_EXISTING=true \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Enable chapter title overlays:**
```bash
# Add chapter titles to video
OVERLAY_CHAPTER_TITLES=true \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

**Combine multiple settings:**
```bash
# Fast processing with overlays, skip existing
WHISPER_MODEL=openai/whisper-base \
OVERLAY_CHAPTER_TITLES=true \
SKIP_EXISTING=true \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input
```

### GPU Configuration Examples

**Select specific GPU (multi-GPU systems):**
```bash
# Use GPU 0
CUDA_VISIBLE_DEVICES=0 \
docker compose run --rm meeting-video-tool-gpu python -m src.main /input

# Use GPU 1
CUDA_VISIBLE_DEVICES=1 \
docker compose run --rm meeting-video-tool-gpu python -m src.main /input
```

**Optimize GPU memory usage:**
```bash
# For GPUs with limited memory
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512 \
docker compose run --rm meeting-video-tool-gpu python -m src.main /input

# For GPUs with ample memory
PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:2048 \
docker compose run --rm meeting-video-tool-gpu python -m src.main /input
```

## Batch Processing Examples

### Simple Batch Processing

**Process multiple files sequentially:**
```bash
#!/bin/bash
# batch-process.sh

set -e
echo "Starting batch processing at $(date)"

# Set common environment variables
export SKIP_EXISTING=true
export WHISPER_MODEL=openai/whisper-medium

# Process each video file
for video in ./videos/*.mkv; do
    if [ -f "$video" ]; then
        echo "Processing: $(basename "$video")"
        docker compose run --rm meeting-video-tool-cpu \
            python -m src.main "/input/$(basename "$video")"
    fi
done

echo "Batch processing completed at $(date)"
```

### Parallel Batch Processing

**Process multiple files in parallel:**
```bash
#!/bin/bash
# parallel-batch-process.sh

set -e
MAX_PARALLEL=2  # Adjust based on your system resources

echo "Starting parallel batch processing at $(date)"
export SKIP_EXISTING=true

for video in ./videos/*.mkv; do
    # Wait if we've reached the maximum number of parallel jobs
    while [ $(jobs -r | wc -l) -ge $MAX_PARALLEL ]; do
        sleep 1
    done
    
    if [ -f "$video" ]; then
        echo "Starting: $(basename "$video")"
        docker compose run --rm meeting-video-tool-cpu \
            python -m src.main "/input/$(basename "$video")" &
    fi
done

# Wait for all background jobs to complete
wait
echo "Parallel batch processing completed at $(date)"
```

### GPU Batch Processing

**Distribute work across multiple GPUs:**
```bash
#!/bin/bash
# gpu-batch-process.sh

set -e
GPU_COUNT=2  # Number of available GPUs

echo "Starting GPU batch processing at $(date)"
export SKIP_EXISTING=true
export WHISPER_MODEL=openai/whisper-large-v3-turbo

videos=(./videos/*.mkv)
for i in "${!videos[@]}"; do
    gpu=$((i % GPU_COUNT))
    video="${videos[$i]}"
    
    if [ -f "$video" ]; then
        echo "Processing $(basename "$video") on GPU $gpu"
        CUDA_VISIBLE_DEVICES=$gpu \
        docker compose run --rm meeting-video-tool-gpu \
            python -m src.main "/input/$(basename "$video")" &
    fi
done

wait
echo "GPU batch processing completed at $(date)"
```

### Scheduled Batch Processing

**Setup automated processing with cron:**
```bash
# Create processing script
cat > /usr/local/bin/process-videos.sh << 'EOF'
#!/bin/bash
cd /path/to/meeting-video-tool
export GEMINI_API_KEY="your_api_key_here"
export SKIP_EXISTING=true

# Log start
echo "$(date): Starting scheduled video processing" >> /var/log/video-processing.log

# Process videos
docker compose run --rm meeting-video-tool-cpu python -m src.main /input >> /var/log/video-processing.log 2>&1

# Log completion
echo "$(date): Completed scheduled video processing" >> /var/log/video-processing.log
EOF

chmod +x /usr/local/bin/process-videos.sh

# Add to crontab (daily at 2 AM)
echo "0 2 * * * /usr/local/bin/process-videos.sh" | crontab -

# View cron logs
tail -f /var/log/video-processing.log
```

## Development Examples

### Development Environment Setup

**Setup for live code development:**
```bash
# Create development override
cat > docker-compose.dev.yml << 'EOF'
version: '3.8'
services:
  meeting-video-tool-cpu:
    volumes:
      - ./src:/app/src:ro  # Mount source code for live reloading
      - ./videos:/input:ro
      - ./output:/output
      - ./cache:/cache
    environment:
      - WHISPER_MODEL=openai/whisper-base  # Fast model for development
      - SKIP_EXISTING=true
      - LOG_LEVEL=DEBUG
    command: ["tail", "-f", "/dev/null"]  # Keep container running
EOF

# Start development environment
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d meeting-video-tool-cpu

# Access container for development
docker compose exec meeting-video-tool-cpu bash
```

### Interactive Development

**Run Python interactively in container:**
```bash
# Start Python REPL
docker compose run --rm meeting-video-tool-cpu python

# Test imports
docker compose run --rm meeting-video-tool-cpu python -c "
import torch
import transformers
import google.generativeai
print('All imports successful')
print(f'PyTorch version: {torch.__version__}')
print(f'CUDA available: {torch.cuda.is_available()}')
"
```

### Testing Different Configurations

**Test model performance:**
```bash
#!/bin/bash
# test-models.sh

test_file="/input/test-short.mkv"  # Use a short test video

echo "Testing different Whisper models..."

for model in base medium large-v3-turbo; do
    echo "Testing whisper-$model..."
    start_time=$(date +%s)
    
    WHISPER_MODEL=openai/whisper-$model \
    docker compose run --rm meeting-video-tool-cpu \
        python -m src.main "$test_file"
    
    end_time=$(date +%s)
    duration=$((end_time - start_time))
    echo "whisper-$model completed in ${duration} seconds"
    echo "---"
done
```

### Debugging Examples

**Debug container issues:**
```bash
# Check container configuration
docker compose config

# View environment variables
docker compose run --rm meeting-video-tool-cpu env

# Check file permissions
docker compose run --rm meeting-video-tool-cpu ls -la /input /output /cache

# Test ffmpeg
docker compose run --rm meeting-video-tool-cpu ffmpeg -version

# Test Python modules
docker compose run --rm meeting-video-tool-cpu python -c "
import sys
print('Python path:')
for path in sys.path:
    print(f'  {path}')
"
```

## Production Examples

### Production Deployment

**Production-ready configuration:**
```bash
# Create production override
cat > docker-compose.prod.yml << 'EOF'
version: '3.8'
services:
  meeting-video-tool-cpu:
    restart: unless-stopped
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - WHISPER_MODEL=openai/whisper-large-v3-turbo
      - SKIP_EXISTING=true
      - LOG_LEVEL=INFO
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
EOF

# Deploy to production
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Load Balancing Example

**Multiple worker setup:**
```bash
# Create multi-worker configuration
cat > docker-compose.workers.yml << 'EOF'
version: '3.8'
services:
  meeting-video-tool-worker-1:
    extends:
      service: meeting-video-tool-cpu
    container_name: video-tool-worker-1
    
  meeting-video-tool-worker-2:
    extends:
      service: meeting-video-tool-cpu
    container_name: video-tool-worker-2
    
  meeting-video-tool-worker-3:
    extends:
      service: meeting-video-tool-cpu
    container_name: video-tool-worker-3

  # Simple load balancer using nginx
  load-balancer:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - meeting-video-tool-worker-1
      - meeting-video-tool-worker-2
      - meeting-video-tool-worker-3
EOF

# Start workers
docker compose -f docker-compose.yml -f docker-compose.workers.yml up -d
```

### Monitoring Example

**Setup monitoring with Prometheus and Grafana:**
```bash
# Create monitoring configuration
cat > docker-compose.monitoring.yml << 'EOF'
version: '3.8'
services:
  prometheus:
    image: prom/prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  prometheus-data:
  grafana-data:
EOF

# Start monitoring stack
docker compose -f docker-compose.yml -f docker-compose.monitoring.yml up -d

# Access Grafana at http://localhost:3000 (admin/admin)
```

## Troubleshooting Examples

### Windows-Specific Issues

**Problem: "Input file not found" with path like "C:/Program Files/Git/input/file.mkv"**

This is a common Windows issue where Git Bash automatically translates Unix-style paths.

```bash
# The problem: Git Bash translates /input/file.mkv to C:/Program Files/Git/input/file.mkv
# Error message: "Input file not found: C:/Program Files/Git/input/2025-12-05 11-01-02.mkv"

# Solution 1: Use PowerShell (recommended)
# Open PowerShell and run:
docker compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Solution 2: Use double slashes in Git Bash
docker compose run --rm meeting-video-tool-cpu python -m src.main //input/meeting.mkv

# Solution 3: Disable path conversion in Git Bash
export MSYS_NO_PATHCONV=1
docker compose run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Solution 4: Use relative paths
docker compose run --rm meeting-video-tool-cpu python -m src.main "input/meeting.mkv"

# Solution 5: Create a batch script for Windows
# Create process-video.bat:
echo @echo off > process-video.bat
echo docker compose run --rm meeting-video-tool-cpu python -m src.main /input/%1 >> process-video.bat
# Then run: process-video.bat meeting.mkv
```

**Windows batch processing script:**
```batch
@echo off
REM batch-process-windows.bat
REM Process all videos in the videos directory on Windows

echo Starting batch processing...

REM Set environment variables
set SKIP_EXISTING=true
set WHISPER_MODEL=openai/whisper-medium

REM Process each .mkv file
for %%f in (videos\*.mkv) do (
    echo Processing: %%f
    docker compose run --rm meeting-video-tool-cpu python -m src.main "/input/%%~nxf"
)

echo Batch processing completed.
pause
```

**PowerShell batch processing script:**
```powershell
# batch-process-windows.ps1
# Process all videos using PowerShell

Write-Host "Starting batch processing..."

# Set environment variables
$env:SKIP_EXISTING = "true"
$env:WHISPER_MODEL = "openai/whisper-medium"

# Get all .mkv files and process them
Get-ChildItem -Path "videos" -Filter "*.mkv" | ForEach-Object {
    Write-Host "Processing: $($_.Name)"
    docker compose run --rm meeting-video-tool-cpu python -m src.main "/input/$($_.Name)"
}

Write-Host "Batch processing completed."
```

### Common Issue Resolution

**Fix permission issues:**
```bash
# Check current permissions
ls -la videos/ output/ cache/

# Fix ownership (replace 1000:1000 with your user:group)
sudo chown -R 1000:1000 videos/ output/ cache/

# Fix permissions
chmod -R 755 videos/ output/ cache/

# For SELinux systems
sudo chcon -Rt svirt_sandbox_file_t videos/ output/ cache/
```

**Resolve memory issues:**
```bash
# Check available memory
free -h

# Check Docker memory limits
docker system info | grep -i memory

# Use smaller model if memory is limited
WHISPER_MODEL=openai/whisper-base \
docker compose run --rm meeting-video-tool-cpu python -m src.main /input

# Clear Docker cache to free space
docker system prune -f
```

**Debug API issues:**
```bash
# Test API key
curl -H "Content-Type: application/json" \
     -d '{"contents":[{"parts":[{"text":"Hello"}]}]}' \
     "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=${GEMINI_API_KEY}"

# Check API quota
echo "Check your API usage at: https://makersuite.google.com/app/apikey"

# Test with minimal request
docker compose run --rm meeting-video-tool-cpu python -c "
import google.generativeai as genai
import os
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
model = genai.GenerativeModel('gemini-pro')
response = model.generate_content('Hello')
print('API test successful:', response.text[:50])
"
```

### Performance Debugging

**Benchmark processing speed:**
```bash
#!/bin/bash
# benchmark.sh

test_video="/input/test.mkv"
echo "Benchmarking processing speed..."

# CPU benchmark
echo "CPU processing..."
time docker compose run --rm meeting-video-tool-cpu python -m src.main "$test_video"

# GPU benchmark (if available)
if docker compose run --rm meeting-video-tool-gpu python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" 2>/dev/null; then
    echo "GPU processing..."
    time docker compose run --rm meeting-video-tool-gpu python -m src.main "$test_video"
else
    echo "GPU not available"
fi

# Model comparison
for model in base medium large-v3-turbo; do
    echo "Testing $model model..."
    time WHISPER_MODEL=openai/whisper-$model \
        docker compose run --rm meeting-video-tool-cpu python -m src.main "$test_video"
done
```

**Monitor resource usage:**
```bash
# Monitor in real-time
docker stats

# Log resource usage
docker stats --no-stream > resource-usage.log

# Monitor GPU usage (if available)
watch -n 1 nvidia-smi

# Check disk usage
docker system df
du -sh cache/ output/ videos/
```

### Network Debugging

**Test connectivity:**
```bash
# Test internet access
docker compose run --rm meeting-video-tool-cpu ping -c 3 google.com

# Test API endpoints
docker compose run --rm meeting-video-tool-cpu curl -s https://generativelanguage.googleapis.com/

# Test model download
docker compose run --rm meeting-video-tool-cpu curl -s https://huggingface.co/

# Check DNS resolution
docker compose run --rm meeting-video-tool-cpu nslookup huggingface.co
```

### Log Analysis

**Analyze container logs:**
```bash
# View recent logs
docker compose logs --tail=100 meeting-video-tool-cpu

# Follow logs in real-time
docker compose logs -f meeting-video-tool-cpu

# Search for errors
docker compose logs meeting-video-tool-cpu | grep -i error

# Export logs for analysis
docker compose logs meeting-video-tool-cpu > processing-logs.txt
```

These examples should cover most common usage scenarios and help troubleshoot issues that may arise during deployment and operation.