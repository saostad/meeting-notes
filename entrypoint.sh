#!/bin/bash
set -e

# Container entrypoint script for Meeting Video Chapter Tool
# Validates environment and system dependencies before starting application

echo "=== Meeting Video Chapter Tool Container ==="
echo "Initializing container environment..."

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to validate environment variables
validate_environment() {
    echo "Validating environment configuration..."
    
    # Check for required API key
    if [ -z "$GEMINI_API_KEY" ]; then
        echo "ERROR: Missing required environment variable: GEMINI_API_KEY"
        echo "Please set GEMINI_API_KEY to your Google Gemini API key."
        echo "Get your API key from: https://makersuite.google.com/app/apikey"
        exit 1
    fi
    
    # Validate API key format (basic check)
    if [[ ! "$GEMINI_API_KEY" =~ ^AIza[0-9A-Za-z_-]{35}$ ]]; then
        echo "WARNING: GEMINI_API_KEY format appears invalid"
        echo "Expected format: AIza followed by 35 characters"
    fi
    
    echo "✓ Required environment variables validated"
}

# Function to detect and configure GPU support
configure_gpu_support() {
    echo "Configuring GPU support..."
    
    # Check if CUDA is available
    local cuda_available=false
    local gpu_count=0
    
    # Check for nvidia-smi command (indicates NVIDIA GPU presence)
    if command_exists nvidia-smi; then
        # Get GPU count and validate CUDA availability
        if gpu_count=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits 2>/dev/null | head -n1); then
            if [ "$gpu_count" -gt 0 ]; then
                cuda_available=true
                echo "✓ Detected $gpu_count NVIDIA GPU(s)"
            fi
        fi
    fi
    
    # Check PyTorch CUDA availability
    local torch_cuda_available=false
    if python -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>/dev/null | grep -q "True"; then
        torch_cuda_available=true
        local torch_cuda_version=$(python -c "import torch; print(torch.version.cuda)" 2>/dev/null || echo "unknown")
        echo "✓ PyTorch CUDA support available (version: $torch_cuda_version)"
    fi
    
    # Set GPU configuration environment variables
    if [ "$cuda_available" = true ] && [ "$torch_cuda_available" = true ]; then
        export CUDA_AVAILABLE=true
        export TORCH_DEVICE=cuda
        # Set default visible devices if not specified
        if [ -z "$CUDA_VISIBLE_DEVICES" ]; then
            export CUDA_VISIBLE_DEVICES=0
        fi
        echo "✓ GPU acceleration enabled (device: cuda:${CUDA_VISIBLE_DEVICES})"
    else
        export CUDA_AVAILABLE=false
        export TORCH_DEVICE=cpu
        echo "ℹ GPU acceleration not available, falling back to CPU processing"
        
        # Log specific reasons for fallback
        if [ "$cuda_available" = false ]; then
            echo "  Reason: No NVIDIA GPU detected or nvidia-smi not available"
        elif [ "$torch_cuda_available" = false ]; then
            echo "  Reason: PyTorch built without CUDA support"
        fi
    fi
}

# Function to check system tool availability
check_system_tools() {
    echo "Checking system tool availability..."
    
    # Check ffmpeg
    if ! command_exists ffmpeg; then
        echo "ERROR: ffmpeg not found in PATH"
        echo "This should not happen in a properly built container"
        exit 1
    fi
    
    # Verify ffmpeg functionality
    if ! ffmpeg -version >/dev/null 2>&1; then
        echo "ERROR: ffmpeg is not functional"
        exit 1
    fi
    
    echo "✓ ffmpeg is available and functional"
    
    # Check Python and required modules
    if ! python -c "import torch, transformers, google.generativeai" >/dev/null 2>&1; then
        echo "ERROR: Required Python modules not available"
        echo "This indicates a problem with the container build"
        exit 1
    fi
    
    echo "✓ Python dependencies validated"
}

# Function to setup directories and permissions
setup_directories() {
    echo "Setting up directories..."
    
    # Ensure volume mount directories exist and are accessible
    for dir in /input /output /cache; do
        if [ ! -d "$dir" ]; then
            echo "WARNING: Directory $dir does not exist, creating..."
            mkdir -p "$dir"
        fi
        
        # Check if directory is writable (for output and cache)
        if [ "$dir" != "/input" ] && [ ! -w "$dir" ]; then
            echo "WARNING: Directory $dir is not writable"
        fi
    done
    
    # Implement default output directory behavior (Requirement 5.4)
    # If OUTPUT_DIR is not specified, default to input directory for co-location
    if [ -z "$OUTPUT_DIR" ]; then
        # Check if /input is mounted and writable
        if [ -d "/input" ] && [ -w "/input" ]; then
            export OUTPUT_DIR="/input"
            echo "✓ Default output directory set to input directory: /input"
        else
            # Fallback to /output if input is not writable
            export OUTPUT_DIR="/output"
            echo "✓ Default output directory set to: /output (input not writable)"
        fi
    else
        echo "✓ Using configured output directory: $OUTPUT_DIR"
    fi
    
    # Ensure the selected output directory exists and is writable
    if [ ! -d "$OUTPUT_DIR" ]; then
        echo "Creating output directory: $OUTPUT_DIR"
        mkdir -p "$OUTPUT_DIR" || {
            echo "ERROR: Cannot create output directory: $OUTPUT_DIR"
            exit 1
        }
    fi
    
    if [ ! -w "$OUTPUT_DIR" ]; then
        echo "ERROR: Output directory is not writable: $OUTPUT_DIR"
        echo "Check volume mount permissions and user ownership"
        exit 1
    fi
    
    echo "✓ Directories configured"
}

# Function to display configuration
display_configuration() {
    echo "Container configuration:"
    echo "  Python version: $(python --version)"
    echo "  ffmpeg version: $(ffmpeg -version 2>&1 | head -n1)"
    echo "  Working directory: $(pwd)"
    echo "  User: $(whoami) (UID: $(id -u))"
    
    # Display GPU configuration
    echo "GPU configuration:"
    echo "  CUDA Available: ${CUDA_AVAILABLE:-false}"
    echo "  PyTorch Device: ${TORCH_DEVICE:-cpu}"
    if [ "$CUDA_AVAILABLE" = "true" ]; then
        echo "  CUDA Visible Devices: ${CUDA_VISIBLE_DEVICES:-0}"
        # Show GPU details if nvidia-smi is available
        if command_exists nvidia-smi; then
            echo "  GPU Details:"
            nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null | sed 's/^/    /' || echo "    Unable to query GPU details"
        fi
    fi
    
    # Display optional configuration
    echo "Environment configuration:"
    echo "  GEMINI_MODEL: ${GEMINI_MODEL:-gemini-flash-latest (default)}"
    echo "  WHISPER_MODEL: ${WHISPER_MODEL:-openai/whisper-large-v3-turbo (default)}"
    echo "  OUTPUT_DIR: ${OUTPUT_DIR}"
    echo "  SKIP_EXISTING: ${SKIP_EXISTING:-false (default)}"
    echo "  OVERLAY_CHAPTER_TITLES: ${OVERLAY_CHAPTER_TITLES:-false (default)}"
    
    # Display model caching configuration (Requirement 7.5)
    echo "Model caching configuration:"
    echo "  HF_HOME: ${HF_HOME:-/cache/huggingface}"
    echo "  TRANSFORMERS_CACHE: ${TRANSFORMERS_CACHE:-/cache/huggingface}"
    echo "  TORCH_HOME: ${TORCH_HOME:-/cache/models}"
    
    # Check cache directory status
    local cache_status="not mounted"
    if [ -d "/cache" ] && [ -w "/cache" ]; then
        cache_status="mounted and writable"
        # Check if cache contains models
        if [ -d "/cache/huggingface" ] && [ "$(ls -A /cache/huggingface 2>/dev/null)" ]; then
            cache_status="mounted with cached models"
        fi
    fi
    echo "  Cache status: ${cache_status}"
    
    # Display volume mount information
    echo "Volume mount configuration:"
    echo "  Input directory: /input ($([ -r /input ] && echo "readable" || echo "not accessible"))"
    echo "  Output directory: ${OUTPUT_DIR} ($([ -w "${OUTPUT_DIR}" ] && echo "writable" || echo "not writable"))"
    echo "  Cache directory: /cache ($([ -w /cache ] && echo "writable" || echo "not writable"))"
    
    # Display file permissions for troubleshooting
    echo "Directory permissions:"
    ls -la / | grep -E "(input|output|cache)" | sed 's/^/  /'
}

# Main initialization
main() {
    validate_environment
    check_system_tools
    configure_gpu_support
    setup_directories
    display_configuration
    
    echo "=== Container initialization complete ==="
    echo ""
    
    # Execute the main application with provided arguments
    exec "$@"
}

# Run main function
main "$@"