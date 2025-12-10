# Makefile for Meeting Video Chapter Tool Docker operations
# Provides convenient commands for building and running the containerized application

.PHONY: help build build-gpu run run-gpu dev clean logs shell test

# Default target
help: ## Show this help message
	@echo "Meeting Video Chapter Tool - Docker Commands"
	@echo "============================================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Prerequisites:"
	@echo "  - Docker and Docker Compose installed"
	@echo "  - For GPU support: NVIDIA Docker runtime"
	@echo "  - Copy .env.example to .env and configure"

# Build targets
build: ## Build CPU-only Docker image
	docker-compose build meeting-video-tool-cpu

build-gpu: ## Build GPU-enabled Docker image (requires NVIDIA Docker)
	docker-compose build meeting-video-tool-gpu

build-all: ## Build both CPU and GPU images
	docker-compose build

# Run targets
run: ## Run CPU-only container (interactive help)
	docker-compose up meeting-video-tool-cpu

run-gpu: ## Run GPU-enabled container (requires NVIDIA Docker)
	docker-compose -f docker-compose.yml -f docker-compose.gpu.yml up meeting-video-tool-gpu

# Development targets
dev: ## Run in development mode with source code mounting
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up meeting-video-tool-cpu

dev-gpu: ## Run GPU development mode
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml -f docker-compose.gpu.yml up meeting-video-tool-gpu

# Process video files
process: ## Process video files in ./videos directory (CPU)
	@if [ ! -f .env ]; then echo "Error: .env file not found. Copy .env.example to .env and configure."; exit 1; fi
	docker-compose run --rm meeting-video-tool-cpu python -m src.main /input

process-gpu: ## Process video files using GPU acceleration
	@if [ ! -f .env ]; then echo "Error: .env file not found. Copy .env.example to .env and configure."; exit 1; fi
	docker-compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm meeting-video-tool-gpu python -m src.main /input

# Utility targets
shell: ## Open shell in CPU container for debugging
	docker-compose run --rm meeting-video-tool-cpu bash

shell-gpu: ## Open shell in GPU container for debugging
	docker-compose -f docker-compose.yml -f docker-compose.gpu.yml run --rm meeting-video-tool-gpu bash

logs: ## Show container logs
	docker-compose logs -f

test: ## Run tests in container
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml run --rm meeting-video-tool-cpu python -m pytest tests/

# Cleanup targets
clean: ## Remove containers and images
	docker-compose down --rmi all --volumes --remove-orphans

clean-cache: ## Clean model cache (WARNING: Will re-download models)
	docker volume rm meeting-video-chapter-tool_model-cache || true
	rm -rf ./cache

# Setup targets
setup: ## Initial setup - copy example files and create directories
	@echo "Setting up Meeting Video Chapter Tool..."
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env file - please configure your API keys"; fi
	@mkdir -p videos output cache
	@echo "Created directories: videos/, output/, cache/"
	@echo "Setup complete! Configure .env file and run 'make build' to get started."

# Check GPU support
check-gpu: ## Check if GPU support is available
	@echo "Checking GPU support..."
	@docker run --rm --gpus all nvidia/cuda:12.1-base-ubuntu20.04 nvidia-smi || echo "GPU support not available"

# Show system info
info: ## Show Docker and system information
	@echo "Docker Information:"
	@echo "=================="
	@docker --version
	@docker-compose --version
	@echo ""
	@echo "Available Images:"
	@docker images | grep meeting-video-tool || echo "No meeting-video-tool images found"
	@echo ""
	@echo "Running Containers:"
	@docker ps | grep meeting-video-tool || echo "No meeting-video-tool containers running"