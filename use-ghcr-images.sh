#!/bin/bash
# Script to configure Docker Compose to use GitHub Container Registry images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if GitHub username is provided
if [ -z "$1" ]; then
    print_error "Please provide your GitHub username"
    echo "Usage: $0 <github_username>"
    echo "Example: $0 johndoe"
    exit 1
fi

GITHUB_USERNAME="$1"

print_status "Configuring Docker Compose to use GHCR images for user: $GITHUB_USERNAME"

# Create .env.ghcr with the provided username
cat > .env.ghcr << EOF
# GitHub Container Registry Configuration
GHCR_USERNAME=$GITHUB_USERNAME
GHCR_IMAGE_CPU=ghcr.io/$GITHUB_USERNAME/meeting-video-tool:cpu
GHCR_IMAGE_GPU=ghcr.io/$GITHUB_USERNAME/meeting-video-tool:gpu

# Application Configuration
# Required: Get your API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_api_key_here

# Model Configuration
GEMINI_MODEL=gemini-flash-latest
WHISPER_MODEL=openai/whisper-large-v3-turbo

# Performance Settings
SKIP_EXISTING=false
OUTPUT_DIR=./output
OVERLAY_CHAPTER_TITLES=false

# GPU Configuration (for multi-GPU systems)
CUDA_VISIBLE_DEVICES=0
EOF

print_status "Created .env.ghcr file"

# Update docker-compose.ghcr.yml with the correct username
sed "s/YOUR_GITHUB_USERNAME/$GITHUB_USERNAME/g" docker-compose.ghcr.yml > docker-compose.ghcr.tmp
mv docker-compose.ghcr.tmp docker-compose.ghcr.yml

print_status "Updated docker-compose.ghcr.yml with your GitHub username"

# Check if images are public or if user needs to login
print_status "Checking if images are accessible..."

# Try to pull the CPU image to test access
if docker pull "ghcr.io/$GITHUB_USERNAME/meeting-video-tool:cpu" > /dev/null 2>&1; then
    print_status "✓ CPU image is accessible"
else
    print_warning "CPU image requires authentication or doesn't exist"
    echo "To login to GHCR, run:"
    echo "  echo \$GITHUB_TOKEN | docker login ghcr.io -u $GITHUB_USERNAME --password-stdin"
fi

# Try to pull the GPU image to test access
if docker pull "ghcr.io/$GITHUB_USERNAME/meeting-video-tool:gpu" > /dev/null 2>&1; then
    print_status "✓ GPU image is accessible"
else
    print_warning "GPU image requires authentication or doesn't exist"
fi

print_status "Configuration complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env.ghcr and add your GEMINI_API_KEY"
echo "2. Use the GHCR images with:"
echo "   docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main /input"
echo ""
echo "Or use the main docker-compose.yml with GHCR images:"
echo "   docker compose --env-file .env.ghcr run --rm meeting-video-tool-cpu python -m src.main /input"