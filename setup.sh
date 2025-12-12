#!/bin/bash
set -e

# Setup script for Meeting Video Chapter Tool
# Handles directory creation, GPU detection, and dependency installation at runtime

echo "=== Meeting Video Chapter Tool Setup ==="
echo "Starting container initialization..."

# Function to log with timestamps
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to create required directories in /workspace with enhanced error handling
create_directories() {
    log "Creating directory structure in /workspace..."
    
    # Create all required subdirectories (Requirements 3.1, 3.5, 5.1-5.5)
    local directories=("models" "logs" "venv" "output" "cache")
    
    # Create Ollama-specific subdirectories
    local ollama_directories=("models/ollama" "models/huggingface")
    
    # Create main directories
    for dir in "${directories[@]}"; do
        local full_path="/workspace/$dir"
        
        if ! mkdir -p "$full_path"; then
            log "✗ ERROR: Failed to create directory $full_path"
            log "  Check disk space and permissions"
            return 1
        fi
        
        if ! chmod 755 "$full_path"; then
            log "⚠ WARNING: Failed to set permissions for $full_path"
            # Don't fail on permission errors, just warn
        fi
        
        # Verify directory is writable
        if ! touch "$full_path/.test_write" 2>/dev/null; then
            log "✗ ERROR: Directory $full_path is not writable"
            return 1
        else
            rm -f "$full_path/.test_write"
        fi
    done
    
    # Create Ollama-specific directories
    for dir in "${ollama_directories[@]}"; do
        local full_path="/workspace/$dir"
        
        if ! mkdir -p "$full_path"; then
            log "✗ ERROR: Failed to create Ollama directory $full_path"
            return 1
        fi
        
        chmod 755 "$full_path" 2>/dev/null || true
    done
    
    # Create cache subdirectories for better organization
    mkdir -p /workspace/cache/{pip,metadata,huggingface} || {
        log "⚠ WARNING: Failed to create cache subdirectories"
    }
    
    log "✓ Directory structure created and validated:"
    log "  - /workspace/models (ML model storage)"
    log "    - /workspace/models/ollama (Ollama models)"
    log "    - /workspace/models/huggingface (Hugging Face models)"
    log "  - /workspace/logs (application and system logs)"
    log "  - /workspace/venv (Python virtual environment)"
    log "  - /workspace/output (processed video files)"
    log "  - /workspace/cache (dependency and model cache)"
    log "    - /workspace/cache/pip (Python package cache)"
    log "    - /workspace/cache/metadata (cache metadata)"
    log "    - /workspace/cache/huggingface (ML model cache)"
    
    return 0
}

# Function to detect GPU and set PyTorch index URL with enhanced error handling
detect_gpu() {
    log "Detecting GPU hardware configuration..."
    
    local pytorch_index="https://download.pytorch.org/whl/cpu"
    local gpu_detected=false
    local gpu_error=""
    
    # Check for NVIDIA GPU using nvidia-smi
    if command_exists nvidia-smi; then
        log "✓ nvidia-smi command found, checking GPU status..."
        
        # Test nvidia-smi functionality with timeout
        if timeout 10 nvidia-smi &>/dev/null; then
            gpu_detected=true
            pytorch_index="https://download.pytorch.org/whl/cu121"
            log "✓ NVIDIA GPU detected - will install CUDA-enabled PyTorch"
            
            # Log detailed GPU information
            local gpu_info=$(nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader 2>/dev/null | head -1)
            if [ -n "$gpu_info" ]; then
                log "  GPU Details: $gpu_info"
            fi
            
            # Check GPU count
            local gpu_count=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits 2>/dev/null | head -n1)
            if [ -n "$gpu_count" ] && [ "$gpu_count" -gt 0 ]; then
                log "  GPU Count: $gpu_count"
            fi
            
            # Verify CUDA runtime is accessible
            if nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits &>/dev/null; then
                log "✓ GPU runtime access verified"
            else
                log "⚠ WARNING: GPU detected but runtime access limited"
                gpu_error="runtime_limited"
            fi
        else
            gpu_error="nvidia_smi_timeout"
            log "⚠ nvidia-smi found but not responding (timeout) - using CPU PyTorch"
            log "  This may indicate GPU driver issues or insufficient permissions"
        fi
    else
        log "ℹ nvidia-smi not found - using CPU PyTorch"
        log "  This is normal for CPU-only systems"
    fi
    
    # Check for other GPU types (future extensibility)
    if [ "$gpu_detected" = false ]; then
        # Check for AMD GPU (basic detection)
        if command_exists rocm-smi || [ -d "/opt/rocm" ]; then
            log "ℹ AMD ROCm detected but not currently supported"
            log "  Using CPU PyTorch (AMD GPU support may be added in future)"
        fi
        
        # Check for Intel GPU (basic detection)
        if lspci 2>/dev/null | grep -i "intel.*graphics" >/dev/null; then
            log "ℹ Intel GPU detected but not currently supported"
            log "  Using CPU PyTorch (Intel GPU support may be added in future)"
        fi
    fi
    
    # Export configuration for use in dependency installation
    export PYTORCH_INDEX_URL="$pytorch_index"
    export GPU_DETECTED="$gpu_detected"
    export GPU_ERROR="$gpu_error"
    
    # Log final configuration
    log "Hardware Configuration Summary:"
    log "  GPU Detected: $gpu_detected"
    log "  PyTorch Index: $(basename "$pytorch_index")"
    if [ -n "$gpu_error" ]; then
        log "  GPU Issues: $gpu_error"
    fi
    
    return 0
}

# Function to check cache integrity and manage cache files
check_cache_integrity() {
    local cache_dir="/workspace/cache"
    local cache_valid=true
    
    log "Checking dependency cache integrity..."
    
    # Create cache metadata directory if it doesn't exist
    mkdir -p "$cache_dir/metadata"
    
    # Check if pip cache is valid
    if [ -d "$cache_dir/pip" ]; then
        # Verify pip cache isn't corrupted by checking a few key files
        if ! find "$cache_dir/pip" -name "*.whl" -o -name "*.tar.gz" | head -5 | while read file; do
            if [ -f "$file" ] && ! file "$file" | grep -q "data"; then
                log "⚠ Corrupted cache file detected: $(basename "$file")"
                return 1
            fi
        done; then
            log "⚠ Pip cache corruption detected, clearing cache..."
            rm -rf "$cache_dir/pip"
            cache_valid=false
        else
            log "✓ Pip cache integrity verified"
        fi
    fi
    
    # Check PyTorch cache validity based on hardware configuration
    local torch_cache_file="$cache_dir/metadata/torch_config"
    local current_config="${GPU_DETECTED}_$(basename "$PYTORCH_INDEX_URL")"
    
    if [ -f "$torch_cache_file" ]; then
        local cached_config=$(cat "$torch_cache_file" 2>/dev/null)
        if [ "$cached_config" != "$current_config" ]; then
            log "ℹ Hardware configuration changed, invalidating PyTorch cache..."
            rm -f "$torch_cache_file"
            # Remove PyTorch-specific cached wheels
            find "$cache_dir/pip" -name "*torch*" -delete 2>/dev/null || true
            cache_valid=false
        else
            log "✓ PyTorch cache matches current hardware configuration"
        fi
    fi
    
    return 0
}

# Function to update cache metadata
update_cache_metadata() {
    local cache_dir="/workspace/cache"
    mkdir -p "$cache_dir/metadata"
    
    # Store current PyTorch configuration
    local torch_cache_file="$cache_dir/metadata/torch_config"
    local current_config="${GPU_DETECTED}_$(basename "$PYTORCH_INDEX_URL")"
    echo "$current_config" > "$torch_cache_file"
    
    # Store dependency installation timestamp
    local deps_cache_file="$cache_dir/metadata/deps_installed"
    date +%s > "$deps_cache_file"
    
    log "✓ Cache metadata updated"
}

# Function to setup Python virtual environment and install dependencies with enhanced caching
setup_dependencies() {
    log "Setting up Python dependencies with caching support..."
    log "DEBUG: SKIP_DEPENDENCY_VALIDATION=${SKIP_DEPENDENCY_VALIDATION:-not_set}"
    
    # Set up pip cache directory (Requirement 4.1)
    export PIP_CACHE_DIR="/workspace/cache/pip"
    mkdir -p "$PIP_CACHE_DIR"
    
    # Check cache integrity before proceeding (Requirement 4.3)
    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
        log "⚠ Skipping cache integrity check (SKIP_DEPENDENCY_VALIDATION=true)"
    else
        check_cache_integrity
    fi
    
    # Check if virtual environment already exists and is valid
    if [ -f "/workspace/venv/bin/activate" ]; then
        log "✓ Virtual environment found, validating..."
        
        # Test if venv is functional with comprehensive checks
        if /workspace/venv/bin/python -c "import sys; print(sys.version)" &>/dev/null; then
            log "✓ Virtual environment is functional"
            source /workspace/venv/bin/activate
            
            # Enhanced dependency checking with cache awareness (Requirement 4.2)
            local deps_cache_file="/workspace/cache/metadata/deps_installed"
            local requirements_hash=$(md5sum /app/requirements.txt | cut -d' ' -f1)
            local cached_hash_file="/workspace/cache/metadata/requirements_hash"
            
            local skip_reinstall=false
            
            # Check if requirements have changed
            if [ -f "$cached_hash_file" ] && [ -f "$deps_cache_file" ]; then
                local cached_hash=$(cat "$cached_hash_file" 2>/dev/null)
                if [ "$cached_hash" = "$requirements_hash" ]; then
                    log "✓ Requirements unchanged, checking existing installation..."
                    
                    # Check cache age for aggressive optimization
                    local cache_age_seconds=$(($(date +%s) - $(cat "$deps_cache_file" 2>/dev/null || echo 0)))
                    local cache_age_hours=$((cache_age_seconds / 3600))
                    
                    # Check for skip file flag or recent cache
                    if [ -f "/workspace/.skip_validation" ] || [ $cache_age_hours -lt 1 ]; then
                        if [ -f "/workspace/.skip_validation" ]; then
                            log "✓ Skipping dependency validation (found /workspace/.skip_validation)"
                        else
                            log "✓ Dependencies recently cached (${cache_age_hours}h ago), skipping validation"
                        fi
                        skip_reinstall=true
                    elif [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
                        log "✓ Skipping dependency validation (SKIP_DEPENDENCY_VALIDATION=true)"
                        skip_reinstall=true
                    elif validate_dependencies_quick; then
                        log "✓ All dependencies validated from cache"
                        skip_reinstall=true
                    else
                        log "⚠ Some dependencies missing, will reinstall..."
                    fi
                else
                    log "ℹ Requirements file changed, will update dependencies..."
                fi
            else
                log "ℹ No cache metadata found, will install dependencies..."
            fi
            
            if [ "$skip_reinstall" = false ]; then
                # Check PyTorch installation and hardware compatibility
                local torch_installed=false
                local torch_cuda_available=false
                
                if python -c "import torch" &>/dev/null; then
                    torch_installed=true
                    if python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" &>/dev/null; then
                        torch_cuda_available=true
                    fi
                fi
                
                # Reinstall PyTorch if hardware configuration changed
                if [ "$torch_installed" = true ]; then
                    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
                        log "✓ PyTorch validation skipped (SKIP_DEPENDENCY_VALIDATION=true)"
                    elif [ "$GPU_DETECTED" = true ] && [ "$torch_cuda_available" = false ]; then
                        log "ℹ GPU detected but PyTorch CPU version installed - upgrading to GPU version"
                        install_pytorch_with_retry
                    elif [ "$GPU_DETECTED" = false ] && [ "$torch_cuda_available" = true ]; then
                        log "ℹ No GPU detected but PyTorch GPU version installed - downgrading to CPU version"
                        install_pytorch_with_retry
                    else
                        log "✓ PyTorch installation matches hardware configuration"
                    fi
                else
                    log "Installing PyTorch for detected hardware configuration..."
                    install_pytorch_with_retry
                fi
                
                # Install/update application requirements with caching
                log "Installing application dependencies with cache..."
                install_requirements_with_retry
                
                # Update cache metadata
                echo "$requirements_hash" > "$cached_hash_file"
                update_cache_metadata
            fi
        else
            log "⚠ Virtual environment is corrupted, recreating..."
            rm -rf /workspace/venv
        fi
    fi
    
    # Create new virtual environment if needed
    if [ ! -f "/workspace/venv/bin/activate" ]; then
        log "Creating new Python virtual environment..."
        
        if ! python -m venv /workspace/venv; then
            log "✗ ERROR: Failed to create virtual environment"
            log "  Check disk space and permissions in /workspace/venv"
            exit 1
        fi
        
        source /workspace/venv/bin/activate
        
        log "Installing Python dependencies with caching..."
        
        # Upgrade pip first with retry logic
        if ! pip install --upgrade pip --cache-dir "$PIP_CACHE_DIR"; then
            log "⚠ Failed to upgrade pip, retrying..."
            if ! pip install --upgrade pip --cache-dir "$PIP_CACHE_DIR" --no-cache-dir; then
                log "✗ ERROR: Failed to upgrade pip after retry"
                exit 1
            fi
        fi
        
        # Install PyTorch with caching and retry logic (Requirements 6.1, 6.2, 6.3)
        install_pytorch_with_retry
        
        # Install other requirements with caching
        install_requirements_with_retry
        
        # Update cache metadata for new installation
        local requirements_hash=$(md5sum /app/requirements.txt | cut -d' ' -f1)
        echo "$requirements_hash" > "/workspace/cache/metadata/requirements_hash"
        update_cache_metadata
        
        log "✓ Dependencies installed successfully with caching"
    else
        source /workspace/venv/bin/activate
    fi
    
    # Final comprehensive validation (Requirement 2.5) - can be skipped for performance
    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
        log "⚠ Skipping comprehensive dependency validation (SKIP_DEPENDENCY_VALIDATION=true)"
        log "✓ Dependencies assumed valid based on cache"
    else
        log "Performing comprehensive dependency validation..."
        if ! validate_dependencies_comprehensive; then
            log "✗ ERROR: Dependency validation failed"
            log "  Some required packages are not properly installed"
            exit 1
        fi
        log "✓ All dependencies validated and cached successfully"
    fi
}

# Function to install PyTorch with retry logic and error handling
install_pytorch_with_retry() {
    local max_retries=3
    local retry_count=0
    
    log "Installing PyTorch ($(basename "$PYTORCH_INDEX_URL")) with caching..."
    
    while [ $retry_count -lt $max_retries ]; do
        if pip install torch torchvision torchaudio --index-url "$PYTORCH_INDEX_URL" --cache-dir "$PIP_CACHE_DIR"; then
            log "✓ PyTorch installed successfully"
            return 0
        else
            retry_count=$((retry_count + 1))
            log "⚠ PyTorch installation failed (attempt $retry_count/$max_retries)"
            
            if [ $retry_count -lt $max_retries ]; then
                log "  Retrying in 5 seconds..."
                sleep 5
                
                # Clear potentially corrupted cache on retry
                if [ $retry_count -eq 2 ]; then
                    log "  Clearing PyTorch cache for clean retry..."
                    find "$PIP_CACHE_DIR" -name "*torch*" -delete 2>/dev/null || true
                fi
            fi
        fi
    done
    
    log "✗ ERROR: Failed to install PyTorch after $max_retries attempts"
    log "  Check network connectivity and disk space"
    log "  PyTorch index URL: $PYTORCH_INDEX_URL"
    exit 1
}

# Function to install requirements with retry logic and error handling
install_requirements_with_retry() {
    local max_retries=3
    local retry_count=0
    
    log "Installing application dependencies with caching..."
    
    while [ $retry_count -lt $max_retries ]; do
        if pip install -r /app/requirements.txt --cache-dir "$PIP_CACHE_DIR"; then
            log "✓ Application dependencies installed successfully"
            return 0
        else
            retry_count=$((retry_count + 1))
            log "⚠ Application dependencies installation failed (attempt $retry_count/$max_retries)"
            
            if [ $retry_count -lt $max_retries ]; then
                log "  Retrying in 3 seconds..."
                sleep 3
            fi
        fi
    done
    
    log "✗ ERROR: Failed to install application dependencies after $max_retries attempts"
    log "  Check network connectivity and requirements.txt file"
    exit 1
}

# Function for quick dependency validation (used for cache checking)
validate_dependencies_quick() {
    # Skip validation if requested for performance
    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
        return 0  # Always return success when skipping
    fi
    
    # Quick check for essential packages
    python -c "import torch, google.generativeai, pytest, hypothesis" &>/dev/null
}

# Function to setup and configure Ollama
setup_ollama() {
    log "Setting up Ollama configuration..."
    
    # Verify Ollama is installed
    if ! command_exists ollama; then
        log "✗ ERROR: Ollama is not installed"
        log "  Ollama should have been installed during Docker build"
        return 1
    fi
    
    # Set Ollama models directory to workspace
    export OLLAMA_MODELS="/workspace/models/ollama"
    
    # Create Ollama configuration directory
    mkdir -p /root/.ollama
    
    # Start Ollama service in background if not already running
    if ! pgrep -f "ollama serve" >/dev/null; then
        log "Starting Ollama service..."
        ollama serve &
        local ollama_pid=$!
        
        # Wait for Ollama to start
        local max_wait=30
        local wait_count=0
        while ! curl -s http://localhost:11434/api/tags >/dev/null 2>&1; do
            if [ $wait_count -ge $max_wait ]; then
                log "⚠ WARNING: Ollama service did not start within ${max_wait}s"
                log "  Ollama models may not be available"
                return 0  # Don't fail the entire setup
            fi
            sleep 1
            wait_count=$((wait_count + 1))
        done
        
        log "✓ Ollama service started successfully"
    else
        log "✓ Ollama service already running"
    fi
    
    # Check if default model should be downloaded
    local default_model="${LOCAL_MODEL_NAME:-phi4}"
    if [ -n "$default_model" ] && [ "$default_model" != "none" ]; then
        log "Checking for default Ollama model: $default_model"
        
        # Check if model exists
        if ! ollama list | grep -q "$default_model"; then
            log "Default model '$default_model' not found, will be downloaded on first use"
            log "  To pre-download: ollama pull $default_model"
        else
            log "✓ Default model '$default_model' is available"
        fi
    fi
    
    log "✓ Ollama setup completed"
    log "  Models directory: /workspace/models/ollama"
    log "  Service endpoint: http://localhost:11434"
    return 0
}

# Function for comprehensive dependency validation
validate_dependencies_comprehensive() {
    local validation_failed=false
    
    # Check PyTorch with detailed validation
    if ! python -c "import torch; print(f'PyTorch {torch.__version__} installed')" 2>/dev/null; then
        log "✗ PyTorch validation failed"
        validation_failed=true
    else
        log "✓ PyTorch validated"
        
        # Validate PyTorch functionality
        if ! python -c "import torch; x = torch.tensor([1.0]); print(f'PyTorch tensor test: {x.item()}')" 2>/dev/null; then
            log "✗ PyTorch functionality test failed"
            validation_failed=true
        else
            log "✓ PyTorch functionality validated"
        fi
    fi
    
    # Check Google Generative AI
    if ! python -c "import google.generativeai; print('Google Generative AI imported successfully')" 2>/dev/null; then
        log "✗ Google Generative AI library validation failed"
        validation_failed=true
    else
        log "✓ Google Generative AI validated"
    fi
    
    # Check testing dependencies
    if ! python -c "import pytest; print(f'pytest {pytest.__version__} available')" 2>/dev/null; then
        log "✗ pytest validation failed"
        validation_failed=true
    else
        log "✓ pytest validated"
    fi
    
    if ! python -c "import hypothesis; print(f'hypothesis {hypothesis.__version__} available')" 2>/dev/null; then
        log "✗ hypothesis validation failed"
        validation_failed=true
    else
        log "✓ hypothesis validated"
    fi
    
    # Check python-dotenv
    if ! python -c "import dotenv; print('python-dotenv available')" 2>/dev/null; then
        log "✗ python-dotenv validation failed"
        validation_failed=true
    else
        log "✓ python-dotenv validated"
    fi
    
    if [ "$validation_failed" = true ]; then
        return 1
    else
        return 0
    fi
}

# Function to validate environment with comprehensive checks
validate_environment() {
    log "Validating environment configuration..."
    local validation_errors=0
    
    # Check for required API key
    if [ -z "$GEMINI_API_KEY" ]; then
        log "⚠ WARNING: GEMINI_API_KEY not set"
        log "  The application will require this environment variable to function"
        log "  Set it when running the container: -e GEMINI_API_KEY=your_key_here"
    else
        # Validate API key format (basic check)
        if [[ "$GEMINI_API_KEY" =~ ^[A-Za-z0-9_-]+$ ]] && [ ${#GEMINI_API_KEY} -gt 10 ]; then
            log "✓ GEMINI_API_KEY is configured and appears valid"
        else
            log "⚠ WARNING: GEMINI_API_KEY format appears invalid"
            log "  Ensure the API key is correct"
        fi
    fi
    
    # Validate workspace mount and permissions
    if [ ! -w "/workspace" ]; then
        log "✗ ERROR: /workspace is not writable"
        log "  Ensure the workspace directory is properly mounted with write permissions"
        validation_errors=$((validation_errors + 1))
    else
        log "✓ Workspace mount is writable"
    fi
    
    # Validate all required directories exist and are accessible
    local required_dirs=("models" "logs" "venv" "output" "cache")
    for dir in "${required_dirs[@]}"; do
        local full_path="/workspace/$dir"
        if [ ! -d "$full_path" ]; then
            log "✗ ERROR: Required directory missing: $full_path"
            validation_errors=$((validation_errors + 1))
        elif [ ! -w "$full_path" ]; then
            log "✗ ERROR: Required directory not writable: $full_path"
            validation_errors=$((validation_errors + 1))
        fi
    done
    
    # Validate Python environment
    if ! python --version >/dev/null 2>&1; then
        log "✗ ERROR: Python is not available"
        validation_errors=$((validation_errors + 1))
    else
        local python_version=$(python --version 2>&1)
        log "✓ Python available: $python_version"
    fi
    
    # Validate ffmpeg availability
    if ! command_exists ffmpeg; then
        log "✗ ERROR: ffmpeg is not available"
        log "  ffmpeg is required for video processing"
        validation_errors=$((validation_errors + 1))
    else
        local ffmpeg_version=$(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f1-3)
        log "✓ ffmpeg available: $ffmpeg_version"
    fi
    
    # Validate network connectivity (basic check)
    if ! curl -s --connect-timeout 5 https://pypi.org >/dev/null; then
        log "⚠ WARNING: Network connectivity to PyPI appears limited"
        log "  This may affect dependency installation"
    else
        log "✓ Network connectivity to PyPI verified"
    fi
    
    # Check system resources
    local memory_mb=$(free -m 2>/dev/null | grep Mem | awk '{print $2}' || echo 0)
    if [ "$memory_mb" -lt 512 ]; then
        log "⚠ WARNING: Low system memory detected (${memory_mb}MB)"
        log "  Consider increasing container memory limits"
    else
        log "✓ System memory: ${memory_mb}MB available"
    fi
    
    # Final validation result
    if [ $validation_errors -gt 0 ]; then
        log "✗ Environment validation failed with $validation_errors errors"
        return 1
    else
        log "✓ Environment validation completed successfully"
        return 0
    fi
}

# Function to display final configuration with enhanced cache information
display_configuration() {
    log "=== Container Configuration Summary ==="
    
    # System information
    log "System Information:"
    log "  Python: $(python --version)"
    log "  ffmpeg: $(ffmpeg -version 2>&1 | head -n1 | cut -d' ' -f1-3)"
    log "  Working directory: $(pwd)"
    
    # GPU configuration
    log "Hardware Configuration:"
    log "  GPU Detected: $GPU_DETECTED"
    if [ "$GPU_DETECTED" = true ]; then
        log "  PyTorch Device: CUDA"
        if command_exists nvidia-smi; then
            local gpu_count=$(nvidia-smi --query-gpu=count --format=csv,noheader,nounits 2>/dev/null | head -n1)
            log "  GPU Count: ${gpu_count:-unknown}"
        fi
    else
        log "  PyTorch Device: CPU"
    fi
    
    # Directory status
    log "Directory Configuration:"
    for dir in models logs venv output cache; do
        local path="/workspace/$dir"
        local status="exists"
        if [ ! -d "$path" ]; then
            status="missing"
        elif [ ! -w "$path" ]; then
            status="read-only"
        fi
        log "  $dir: $status"
    done
    
    # Enhanced cache status and statistics (Requirement 4.1, 4.2)
    log "Cache Configuration:"
    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
        log "  Cache details: skipped (SKIP_DEPENDENCY_VALIDATION=true)"
        if [ -f "/workspace/cache/metadata/deps_installed" ]; then
            local install_time=$(cat /workspace/cache/metadata/deps_installed 2>/dev/null)
            if [ -n "$install_time" ]; then
                local cache_age_seconds=$(($(date +%s) - $install_time))
                local cache_age_hours=$((cache_age_seconds / 3600))
                if [ $cache_age_hours -lt 24 ]; then
                    log "  Status: fresh (${cache_age_hours}h old)"
                else
                    local cache_age_days=$((cache_age_hours / 24))
                    log "  Status: aged (${cache_age_days}d old)"
                fi
            fi
        fi
    elif [ -d "/workspace/cache" ]; then
        local cache_size=$(du -sh /workspace/cache 2>/dev/null | cut -f1)
        log "  Total cache size: ${cache_size:-0B}"
        
        # Pip cache details
        if [ -d "/workspace/cache/pip" ]; then
            local pip_cache_size=$(du -sh /workspace/cache/pip 2>/dev/null | cut -f1)
            local pip_cache_files=$(find /workspace/cache/pip -type f 2>/dev/null | wc -l)
            log "  Pip cache: ${pip_cache_size:-0B} (${pip_cache_files} files)"
        else
            log "  Pip cache: not initialized"
        fi
        
        # Cache metadata
        if [ -f "/workspace/cache/metadata/deps_installed" ]; then
            local install_time=$(cat /workspace/cache/metadata/deps_installed 2>/dev/null)
            if [ -n "$install_time" ]; then
                local install_date=$(date -d "@$install_time" 2>/dev/null || echo "unknown")
                log "  Last dependency install: $install_date"
            fi
        fi
        
        if [ -f "/workspace/cache/metadata/torch_config" ]; then
            local torch_config=$(cat /workspace/cache/metadata/torch_config 2>/dev/null)
            log "  PyTorch cache config: $torch_config"
        fi
        
        if [ -f "/workspace/cache/metadata/requirements_hash" ]; then
            local req_hash=$(cat /workspace/cache/metadata/requirements_hash 2>/dev/null)
            log "  Requirements hash: ${req_hash:0:8}..."
        fi
    else
        log "  Cache directory: not available"
    fi
    
    # Dependency validation summary
    log "Dependency Status:"
    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
        log "  All core dependencies: ✓ skipped (SKIP_DEPENDENCY_VALIDATION=true)"
    elif validate_dependencies_quick; then
        log "  All core dependencies: ✓ validated"
    else
        log "  Core dependencies: ⚠ validation issues detected"
    fi
    
    # Performance metrics
    log "Performance Metrics:"
    log "  Total setup time: ${SECONDS}s"
    
    # Calculate cache hit rate if possible
    if [ -f "/workspace/cache/metadata/deps_installed" ]; then
        local cache_age_seconds=$(($(date +%s) - $(cat /workspace/cache/metadata/deps_installed 2>/dev/null || echo 0)))
        local cache_age_hours=$((cache_age_seconds / 3600))
        if [ $cache_age_hours -lt 24 ]; then
            log "  Cache status: fresh (${cache_age_hours}h old)"
        else
            local cache_age_days=$((cache_age_hours / 24))
            log "  Cache status: aged (${cache_age_days}d old)"
        fi
    fi
    
    log "=== Setup Complete ==="
    log ""
}

# Function to handle cleanup on error
cleanup_on_error() {
    local exit_code=$?
    log "✗ ERROR: Setup failed with exit code $exit_code"
    log "Performing cleanup..."
    
    # Log system state for debugging
    log "System state at failure:"
    log "  Disk space: $(df -h /workspace 2>/dev/null | tail -1 | awk '{print $4}' || echo 'unknown') available"
    log "  Memory usage: $(free -h 2>/dev/null | grep Mem | awk '{print $3"/"$2}' || echo 'unknown')"
    
    # Clean up partial installations if they exist
    if [ -d "/workspace/venv" ] && [ ! -f "/workspace/venv/bin/activate" ]; then
        log "Cleaning up incomplete virtual environment..."
        rm -rf /workspace/venv
    fi
    
    # Preserve logs for debugging
    if [ -d "/workspace/logs" ]; then
        local error_log="/workspace/logs/setup_error_$(date +%Y%m%d_%H%M%S).log"
        echo "Setup failed at $(date)" > "$error_log"
        echo "Exit code: $exit_code" >> "$error_log"
        echo "Command line: $0 $*" >> "$error_log"
        log "Error details saved to: $error_log"
    fi
    
    exit $exit_code
}

# Quick setup for simple commands (Ollama, version checks, etc.)
quick_setup() {
    log "Quick setup mode for: $*"
    
    # Create basic directories
    mkdir -p /workspace/{models/ollama,logs,cache}
    
    # Set Ollama environment
    export OLLAMA_MODELS="/workspace/models/ollama"
    
    # Start Ollama if needed
    if [[ "$*" == *"ollama"* ]]; then
        if ! pgrep -f "ollama serve" >/dev/null; then
            log "Starting Ollama service (quick mode)..."
            ollama serve &
            sleep 3  # Brief wait for startup
        fi
    fi
    
    log "✓ Quick setup completed"
    exec "$@"
}

# Enhanced main setup function with comprehensive error handling
main() {
    local start_time=$SECONDS
    
    # Check if this is a simple command that doesn't need full setup
    case "$1" in
        "ollama"|"echo"|"ls"|"cat"|"which"|"--version"|"-v")
            quick_setup "$@"
            return
            ;;
    esac
    
    # Set up error handling (Requirement 7.3)
    trap cleanup_on_error ERR
    set -e  # Exit on any error
    
    log "Container initialization started with PID $$"
    log "Command line arguments: $*"
    
    # Enhanced workspace validation with detailed error messages
    if [ ! -d "/workspace" ]; then
        log "✗ ERROR: /workspace directory not found"
        log "  The container requires a host directory mounted to /workspace"
        log "  Example: docker run -v ./workspace:/workspace ..."
        log "  Ensure the host directory exists and has proper permissions"
        exit 1
    fi
    
    # Check workspace permissions early
    if [ ! -w "/workspace" ]; then
        log "✗ ERROR: /workspace is not writable"
        log "  The container user needs write access to the mounted directory"
        log "  Try: chmod 755 ./workspace on the host system"
        exit 1
    fi
    
    # Check available disk space
    local available_space=$(df /workspace | tail -1 | awk '{print $4}')
    local min_space_kb=1048576  # 1GB minimum
    if [ "$available_space" -lt "$min_space_kb" ]; then
        log "✗ ERROR: Insufficient disk space in /workspace"
        log "  Available: $(($available_space / 1024))MB, Required: $(($min_space_kb / 1024))MB"
        log "  Free up disk space on the host system"
        exit 1
    fi
    
    log "✓ Workspace validation passed ($(($available_space / 1024))MB available)"
    
    # Run setup steps with enhanced error handling
    log "Executing setup phases..."
    
    if ! create_directories; then
        log "✗ ERROR: Failed to create directory structure"
        exit 1
    fi
    
    if ! detect_gpu; then
        log "✗ ERROR: Failed to detect GPU configuration"
        exit 1
    fi
    
    if ! setup_dependencies; then
        log "✗ ERROR: Failed to setup dependencies"
        exit 1
    fi
    
    if ! setup_ollama; then
        log "✗ ERROR: Failed to setup Ollama"
        exit 1
    fi
    
    if [ "${SKIP_DEPENDENCY_VALIDATION:-false}" = "true" ]; then
        log "⚠ Skipping environment validation (SKIP_DEPENDENCY_VALIDATION=true)"
    else
        if ! validate_environment; then
            log "✗ ERROR: Environment validation failed"
            exit 1
        fi
    fi
    
    # Display final configuration
    display_configuration
    
    # Log successful completion
    log "✓ Container setup completed successfully in ${SECONDS}s"
    
    # Execute the main application with provided arguments
    if [ $# -gt 0 ]; then
        log "Starting application with arguments: $*"
        # Ensure virtual environment is activated before running the application
        source /workspace/venv/bin/activate
        exec "$@"
    else
        log "No application command provided, entering interactive mode"
        source /workspace/venv/bin/activate
        exec /bin/bash
    fi
}

# Run main function with all arguments
main "$@"