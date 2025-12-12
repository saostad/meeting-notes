# Docker Development Environment Files

## Core Files (Clean & Minimal)

### Docker Configuration
- **`Dockerfile`** - Minimal Docker image definition with Ollama integration
- **`docker-compose.yml`** - Unified container orchestration (no separate dev/prod files)
- **`setup.sh`** - Intelligent runtime setup script with quick mode and Ollama support

### Documentation
- **`DOCKER_DEV_README.md`** - Complete Docker development environment guide
- **`README.md`** - Main application documentation (includes Docker usage)
- **`DOCKER_SETUP_FILES.md`** - This file overview

### Validation & Testing
- **`test_docker_setup_validation.py`** - Configuration validation script

## Key Features Implemented

✅ **Minimal Docker Image** (~770MB with Ollama)  
✅ **Runtime Dependency Management** (fresh dependencies, smart caching)  
✅ **Single Host Mount** (`./workspace/` contains everything)  
✅ **Hardware Auto-Detection** (GPU/CPU with automatic PyTorch selection)  
✅ **Ollama Integration** (local AI models with host persistence)  
✅ **Quick Setup Mode** (3-second startup for Ollama commands)  
✅ **Development Features** (live code mounting, interactive mode)  
✅ **Simplified Configuration** (single docker-compose.yml, no complex overrides)  
✅ **Clean File Structure** (removed 15+ obsolete Docker files)  

## Usage

### Quick Start
```bash
# Build environment
docker-compose build

# Fast Ollama operations (3-5 seconds)
docker-compose run --rm app ollama pull phi4
docker-compose run --rm app ollama list

# Full application (with complete setup)
docker-compose run --rm app python -m src.main video.mkv
```

### Validation
```bash
# Validate configuration
python test_docker_setup_validation.py
```

## Directory Structure

```
./workspace/                    # Single host mount (persistent)
├── models/
│   ├── ollama/                # Ollama models (phi4, llama3, etc.)
│   └── huggingface/           # Hugging Face models (Whisper, etc.)
├── logs/                      # Application logs
├── venv/                      # Python virtual environment
├── output/                    # Processed videos
└── cache/                     # Dependency cache
    ├── pip/                   # Python packages
    ├── metadata/              # Cache validation
    └── huggingface/           # ML model cache
```

## Performance

- **First Run**: 2-5 minutes (downloads dependencies)
- **Subsequent Runs**: 10-30 seconds (uses cache)
- **Ollama Commands**: 3-5 seconds (quick setup mode)
- **Model Storage**: Host-persisted in `./workspace/models/ollama/`