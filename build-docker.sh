#!/bin/bash
# Build script for Meeting Video Chapter Tool Docker images
# Supports building both CPU and GPU variants

set -e

# Default values
IMAGE_NAME="meeting-video-tool"
BUILD_TYPE="cpu"
TAG_SUFFIX=""

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --type TYPE     Build type: cpu, gpu, or both (default: cpu)"
    echo "  -n, --name NAME     Image name (default: meeting-video-tool)"
    echo "  -s, --suffix SUFFIX Tag suffix (default: none)"
    echo "  -h, --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --type cpu                    # Build CPU-only image"
    echo "  $0 --type gpu                    # Build GPU-enabled image"
    echo "  $0 --type both                   # Build both variants"
    echo "  $0 --type gpu --suffix v1.0      # Build GPU image with tag suffix"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--type)
            BUILD_TYPE="$2"
            shift 2
            ;;
        -n|--name)
            IMAGE_NAME="$2"
            shift 2
            ;;
        -s|--suffix)
            TAG_SUFFIX="-$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate build type
if [[ ! "$BUILD_TYPE" =~ ^(cpu|gpu|both)$ ]]; then
    echo "Error: Invalid build type '$BUILD_TYPE'. Must be cpu, gpu, or both."
    exit 1
fi

# Function to build CPU image
build_cpu() {
    echo "Building CPU-only image with performance optimizations..."
    docker build \
        --build-arg PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cpu \
        --build-arg ENABLE_GPU=false \
        -t "${IMAGE_NAME}:cpu${TAG_SUFFIX}" \
        -t "${IMAGE_NAME}:latest${TAG_SUFFIX}" \
        .
    echo "✓ CPU image built: ${IMAGE_NAME}:cpu${TAG_SUFFIX}"
    echo "  Features: Model caching, skip-existing, multi-stage build optimization"
}

# Function to build GPU image
build_gpu() {
    echo "Building GPU-enabled image with performance optimizations..."
    docker build \
        --build-arg PYTORCH_INDEX_URL=https://download.pytorch.org/whl/cu121 \
        --build-arg ENABLE_GPU=true \
        -t "${IMAGE_NAME}:gpu${TAG_SUFFIX}" \
        .
    echo "✓ GPU image built: ${IMAGE_NAME}:gpu${TAG_SUFFIX}"
    echo "  Features: GPU acceleration, model caching, skip-existing, multi-stage build optimization"
}

# Create cache directory for model persistence (Requirement 7.5)
echo "Setting up model cache directory..."
mkdir -p ./cache/huggingface
mkdir -p ./cache/models

# Main build logic
echo "=== Meeting Video Chapter Tool Docker Build ==="
echo "Build type: $BUILD_TYPE"
echo "Image name: $IMAGE_NAME"
echo "Tag suffix: ${TAG_SUFFIX:-none}"
echo "Performance optimizations: enabled"
echo ""

case $BUILD_TYPE in
    cpu)
        build_cpu
        ;;
    gpu)
        build_gpu
        ;;
    both)
        build_cpu
        echo ""
        build_gpu
        ;;
esac

echo ""
echo "=== Build Complete ==="
echo "Available images:"
docker images "${IMAGE_NAME}" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"
echo ""
echo "Performance features included:"
echo "  ✓ Model caching enabled (./cache directory created)"
echo "  ✓ Multi-stage build for optimized image size"
echo "  ✓ Support for Whisper model variants (base, medium, large, large-v3-turbo)"
echo "  ✓ Skip-existing functionality for faster reprocessing"
echo "  ✓ Cleanup steps to minimize image size"
echo ""
echo "Usage examples:"
echo "  # Run with Docker Compose (recommended):"
echo "  docker-compose up meeting-video-tool"
echo ""
echo "  # Run directly with model caching:"
echo "  docker run --rm \\"
echo "    -v \$(pwd)/videos:/input:ro \\"
echo "    -v \$(pwd)/output:/output \\"
echo "    -v \$(pwd)/cache:/cache \\"
echo "    -e GEMINI_API_KEY=your_key \\"
echo "    -e WHISPER_MODEL=openai/whisper-large-v3-turbo \\"
echo "    -e SKIP_EXISTING=true \\"
echo "    ${IMAGE_NAME}:latest python -m src.main /input/your_video.mkv"