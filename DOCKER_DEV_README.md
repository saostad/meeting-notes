# Docker Development Environment

A containerized development environment that ensures consistency between development and deployment while using minimal Docker images with runtime dependency management.

## Quick Start

### Prerequisites

- Docker Engine 20.10+
- For GPU support: NVIDIA Container Toolkit (optional)

### Build and Run

1. **Build the development environment:**
   ```bash
   docker-compose build
   ```

2. **Start the development container:**
   ```bash
   # Set your API key
   export GEMINI_API_KEY=your_api_key_here
   
   # Run the container
   docker-compose up app
   ```

3. **Process a video file:**
   ```bash
   # Place your video in the videos/ directory, then:
   docker-compose run --rm app python -m src.main /videos/your-meeting.mkv
   ```

## Key Features

### ✅ Minimal Base Image
- **Small footprint**: ~100MB base image (Python 3.12 slim + ffmpeg)
- **Runtime dependencies**: Downloads Python packages on first run
- **Fresh dependencies**: Always uses latest compatible versions

### ✅ Single Host Mount
- **Everything in one place**: Single `./workspace/` directory contains all persistent data
- **Auto-organized**: Container creates and manages subdirectories:
  - `models/` - ML model storage
  - `logs/` - Application and system logs  
  - `venv/` - Python virtual environment
  - `output/` - Processed video files
  - `cache/` - Dependency and model cache

### ✅ Smart Caching
- **Fast restarts**: Dependencies cached after first installation
- **Intelligent invalidation**: Automatically detects when dependencies need updating
- **Shared cache**: Multiple containers share the same cached dependencies

### ✅ Hardware Auto-Detection
- **GPU support**: Automatically detects and configures NVIDIA GPUs
- **CPU fallback**: Gracefully falls back to CPU processing when GPU unavailable
- **Consistent behavior**: Same application behavior regardless of hardware

### ✅ Local AI Models (Ollama)
- **Ollama integration**: Built-in Ollama server for local AI models
- **Model persistence**: Models stored in `./workspace/models/ollama/` on host
- **API access**: Ollama API available at `http://localhost:11434`
- **Popular models**: Easy access to phi4, llama3, mistral, and other models

## Directory Structure

After first run, your workspace will contain:

```
./workspace/
├── models/          # Downloaded ML models
│   ├── ollama/      # Ollama models (phi4, llama3, etc.)
│   └── huggingface/ # Hugging Face models (Whisper, etc.)
├── logs/           # Container and application logs
├── venv/           # Python virtual environment
├── output/         # Processed video files
└── cache/          # Dependency cache
    ├── pip/        # Python package cache
    ├── metadata/   # Cache metadata and validation
    └── huggingface/ # ML model cache
```

## Configuration

### Environment Variables

Set these in your `.env` file or pass with `-e`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | **Yes** | - | Google Gemini API key |
| `WHISPER_MODEL` | No | `openai/whisper-large-v3-turbo` | Whisper model for transcription |
| `LOCAL_MODEL_NAME` | No | `phi4` | Default Ollama model to use |
| `AI_PROVIDER` | No | `gemini` | AI provider (gemini, ollama) |
| `DEVELOPMENT_MODE` | No | `true` | Enable development features |

### GPU Support

**Automatic detection** - no configuration needed:
- Container detects GPU availability on startup
- Downloads appropriate PyTorch version (CPU/CUDA)
- Falls back to CPU if GPU unavailable

**Manual GPU control:**
```bash
# Force CPU-only
docker-compose run -e CUDA_VISIBLE_DEVICES= app python -m src.main video.mkv

# Use specific GPU
docker-compose run -e CUDA_VISIBLE_DEVICES=0 app python -m src.main video.mkv
```

## Usage Examples

### Basic Video Processing
```bash
# Process a meeting video
docker-compose run --rm app python -m src.main /videos/meeting.mkv
```

### Development Mode
```bash
# Interactive shell for development
docker-compose run --rm app /bin/bash

# Run tests
docker-compose run --rm app python -m pytest tests/

# Check dependencies
docker-compose run --rm app python -c "import torch; print(torch.__version__)"
```

### Batch Processing
```bash
# Process multiple videos
for video in videos/*.mkv; do
    docker-compose run --rm app python -m src.main "/videos/$(basename "$video")"
done
```

### Using Local AI Models (Ollama)

**Download and use local models:**
```bash
# Download a model (one-time setup)
docker-compose run --rm app ollama pull phi4

# Use local AI provider
docker-compose run --rm -e AI_PROVIDER=ollama app python -m src.main /videos/meeting.mkv

# List available models
docker-compose run --rm app ollama list

# Interactive Ollama session
docker-compose run --rm app ollama run phi4
```

**Popular Ollama models:**
- `phi4` - Microsoft's latest small model (3.8B parameters)
- `llama3.2` - Meta's Llama 3.2 (3B/1B parameters)
- `mistral` - Mistral 7B model
- `qwen2.5` - Alibaba's Qwen 2.5 model

**Model management:**
```bash
# Download specific model
docker-compose run --rm app ollama pull llama3.2

# Remove model to save space
docker-compose run --rm app ollama rm phi4

# Check model info
docker-compose run --rm app ollama show phi4

# Interactive chat with model
docker-compose run --rm app ollama run phi4
```

## Performance

### First Run (Cold Cache)
- **Setup time**: 2-5 minutes (downloads dependencies)
- **Disk usage**: ~2GB (dependencies) + model sizes
- **Ollama models**: 2-8GB per model (stored on host)

### Subsequent Runs (Warm Cache)
- **Startup time**: 10-30 seconds
- **Processing**: Same as native installation
- **Ollama startup**: Additional 5-10 seconds for service

### Optimization Tips
1. **Keep workspace**: Don't delete `./workspace/` between runs
2. **GPU acceleration**: 5-10x faster transcription with NVIDIA GPU
3. **Batch processing**: Process multiple files in same container session

## Troubleshooting

### Container Won't Start
```bash
# Check Docker is running
docker --version

# Check image exists
docker images | grep meeting-video-tool

# Rebuild if needed
docker-compose build --no-cache
```

### Permission Issues
```bash
# Fix workspace permissions (Linux/macOS)
sudo chown -R $USER:$USER ./workspace/
chmod -R 755 ./workspace/

# Windows: Run Docker Desktop as Administrator
```

### Slow Performance
```bash
# Check if using GPU
docker-compose run --rm app python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# Clear cache and rebuild
rm -rf ./workspace/cache/
docker-compose build --no-cache
```

### Out of Disk Space
```bash
# Check workspace size
du -sh ./workspace/

# Clean old cache
rm -rf ./workspace/cache/pip/
rm -rf ./workspace/cache/huggingface/

# Clean Docker system
docker system prune -f
```

## Development

### Running Tests
```bash
# Test the Docker environment
python test_docker_dev_environment.py

# Test application functionality
docker-compose run --rm app python -m pytest tests/
```

### Modifying the Setup
- **Dockerfile**: Minimal base image configuration
- **setup.sh**: Runtime dependency installation and configuration
- **docker-compose.yml**: Container orchestration and volume mounts

### Adding Dependencies
1. Add to `requirements.txt`
2. Restart container (dependencies auto-detected and installed)

## Architecture

The development environment uses a **minimal base + runtime setup** approach:

1. **Build time**: Only essential system packages (Python, ffmpeg)
2. **Runtime**: Downloads and caches Python dependencies on first run
3. **Caching**: Smart cache invalidation based on requirements changes
4. **Hardware**: Auto-detects GPU and configures appropriate dependencies

This ensures:
- ✅ Small Docker images
- ✅ Fresh dependencies
- ✅ Fast subsequent startups
- ✅ Consistent dev/prod environments

## Support

For issues specific to the Docker environment:
1. Check container logs: `docker-compose logs app`
2. Run tests: `python test_docker_dev_environment.py`
3. Verify setup: `docker-compose run --rm app ./setup.sh --help`

For application issues, see the main [README.md](README.md).