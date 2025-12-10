# Using Pre-built Images from GitHub Container Registry

This document explains how to use the pre-built Docker images hosted on GitHub Container Registry (GHCR) instead of building them locally.

## Benefits of Using GHCR Images

- ✅ **No build time** - Images are ready to use immediately
- ✅ **Consistent environment** - Same image works across all systems
- ✅ **Smaller download** - Only download what you need (CPU or GPU)
- ✅ **Automatic updates** - Pull latest versions easily
- ✅ **No Docker build dependencies** - No need for build tools

## Quick Setup

### 1. Configure for GHCR Images

**Linux/macOS:**
```bash
# Replace 'your_github_username' with the actual username
./use-ghcr-images.sh your_github_username
```

**Windows:**
```batch
REM Replace 'your_github_username' with the actual username
use-ghcr-images.bat your_github_username
```

### 2. Add Your API Key

Edit the generated `.env.ghcr` file:
```bash
# Edit .env.ghcr
GEMINI_API_KEY=your_actual_api_key_here
```

### 3. Run with GHCR Images

**CPU Processing:**
```bash
# Process a single video
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv

# Process all videos in directory
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main /input
```

**GPU Processing:**
```bash
# Process with GPU acceleration (requires GPU setup)
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-gpu python -m src.main /input/meeting.mkv
```

## Alternative Usage Methods

### Method 1: Using Main docker-compose.yml with GHCR

After running the setup script, you can use the main docker-compose.yml:

```bash
# The setup script configures environment variables for GHCR images
docker compose --env-file .env.ghcr run --rm meeting-video-tool-cpu python -m src.main /input
```

### Method 2: Direct Docker Run

```bash
# CPU processing
docker run --rm \
  -v $(pwd)/videos:/input:ro \
  -v $(pwd)/output:/output \
  -v $(pwd)/cache:/cache \
  -e GEMINI_API_KEY=your_key \
  ghcr.io/your_github_username/meeting-video-tool:cpu \
  python -m src.main /input/meeting.mkv

# GPU processing
docker run --rm --gpus all \
  -v $(pwd)/videos:/input:ro \
  -v $(pwd)/output:/output \
  -v $(pwd)/cache:/cache \
  -e GEMINI_API_KEY=your_key \
  ghcr.io/your_github_username/meeting-video-tool:gpu \
  python -m src.main /input/meeting.mkv
```

### Method 3: Pull Images Manually

```bash
# Pull CPU image
docker pull ghcr.io/your_github_username/meeting-video-tool:cpu

# Pull GPU image
docker pull ghcr.io/your_github_username/meeting-video-tool:gpu

# List downloaded images
docker images | grep meeting-video-tool
```

## Authentication (If Images are Private)

If the images are private, you'll need to authenticate:

```bash
# Login to GHCR
echo $GITHUB_TOKEN | docker login ghcr.io -u your_github_username --password-stdin

# Then pull/run images as normal
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml pull
```

## Windows-Specific Usage

**PowerShell (Recommended):**
```powershell
# Process video (use PowerShell to avoid path translation issues)
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv
```

**Git Bash (with path fix):**
```bash
# Use double slashes to prevent path translation
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main //input/meeting.mkv

# Or disable path conversion
MSYS_NO_PATHCONV=1 docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main /input/meeting.mkv
```

## Configuration Options

The `.env.ghcr` file supports all the same configuration options as the main `.env` file:

```bash
# Model selection (affects speed vs accuracy)
WHISPER_MODEL=openai/whisper-base          # Fastest
WHISPER_MODEL=openai/whisper-medium        # Balanced
WHISPER_MODEL=openai/whisper-large-v3-turbo # Best quality

# Performance options
SKIP_EXISTING=true                         # Skip existing files
OVERLAY_CHAPTER_TITLES=true               # Add chapter overlays

# GPU configuration
CUDA_VISIBLE_DEVICES=0                    # Select specific GPU
```

## Updating Images

To get the latest version of the images:

```bash
# Pull latest images
docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml pull

# Or pull specific images
docker pull ghcr.io/your_github_username/meeting-video-tool:cpu
docker pull ghcr.io/your_github_username/meeting-video-tool:gpu
```

## Troubleshooting

**Problem: "Image not found"**
- Verify the GitHub username is correct
- Check if images are public or if you need to authenticate
- Ensure the images were successfully uploaded to GHCR

**Problem: "Permission denied"**
- Login to GHCR: `echo $GITHUB_TOKEN | docker login ghcr.io -u username --password-stdin`
- Verify your GitHub token has `read:packages` permission

**Problem: "Path translation on Windows"**
- Use PowerShell instead of Git Bash
- Or use double slashes: `//input/file.mkv`
- Or set `MSYS_NO_PATHCONV=1` in Git Bash

**Problem: "Out of disk space"**
- The GPU image is large (10GB+), ensure sufficient disk space
- Clean up old images: `docker system prune -f`

## File Structure

After setup, your directory should look like:

```
meeting-video-tool/
├── .env.ghcr                    # GHCR configuration
├── docker-compose.ghcr.yml     # GHCR-specific compose file
├── docker-compose.yml          # Main compose file (supports both local and GHCR)
├── use-ghcr-images.sh          # Setup script (Linux/macOS)
├── use-ghcr-images.bat         # Setup script (Windows)
├── videos/                     # Input videos
├── output/                     # Processed output
└── cache/                      # Model cache
```

## Performance Comparison

| Method | Build Time | First Run | Subsequent Runs | Disk Usage |
|--------|------------|-----------|-----------------|------------|
| Local Build | 15-30 min | Fast | Fast | ~12GB |
| GHCR CPU | 0 min | 2-5 min download | Fast | ~3GB |
| GHCR GPU | 0 min | 10-15 min download | Fast | ~10GB |

The GHCR images are optimized and may be smaller than locally built images due to better layer caching and optimization.