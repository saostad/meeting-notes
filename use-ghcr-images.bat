@echo off
REM Script to configure Docker Compose to use GitHub Container Registry images

setlocal enabledelayedexpansion

if "%1"=="" (
    echo [ERROR] Please provide your GitHub username
    echo Usage: %0 ^<github_username^>
    echo Example: %0 johndoe
    exit /b 1
)

set GITHUB_USERNAME=%1

echo [INFO] Configuring Docker Compose to use GHCR images for user: %GITHUB_USERNAME%

REM Create .env.ghcr with the provided username
(
echo # GitHub Container Registry Configuration
echo GHCR_USERNAME=%GITHUB_USERNAME%
echo GHCR_IMAGE_CPU=ghcr.io/%GITHUB_USERNAME%/meeting-video-tool:cpu
echo GHCR_IMAGE_GPU=ghcr.io/%GITHUB_USERNAME%/meeting-video-tool:gpu
echo.
echo # Application Configuration
echo # Required: Get your API key from https://makersuite.google.com/app/apikey
echo GEMINI_API_KEY=your_api_key_here
echo.
echo # Model Configuration
echo GEMINI_MODEL=gemini-flash-latest
echo WHISPER_MODEL=openai/whisper-large-v3-turbo
echo.
echo # Performance Settings
echo SKIP_EXISTING=false
echo OUTPUT_DIR=./output
echo OVERLAY_CHAPTER_TITLES=false
echo.
echo # GPU Configuration ^(for multi-GPU systems^)
echo CUDA_VISIBLE_DEVICES=0
) > .env.ghcr

echo [INFO] Created .env.ghcr file

REM Update docker-compose.ghcr.yml with the correct username
powershell -Command "(Get-Content docker-compose.ghcr.yml) -replace 'YOUR_GITHUB_USERNAME', '%GITHUB_USERNAME%' | Set-Content docker-compose.ghcr.yml"

echo [INFO] Updated docker-compose.ghcr.yml with your GitHub username

echo [INFO] Checking if images are accessible...

REM Try to pull the CPU image to test access
docker pull ghcr.io/%GITHUB_USERNAME%/meeting-video-tool:cpu >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] ✓ CPU image is accessible
) else (
    echo [WARNING] CPU image requires authentication or doesn't exist
    echo To login to GHCR, run:
    echo   echo %%GITHUB_TOKEN%% ^| docker login ghcr.io -u %GITHUB_USERNAME% --password-stdin
)

REM Try to pull the GPU image to test access
docker pull ghcr.io/%GITHUB_USERNAME%/meeting-video-tool:gpu >nul 2>&1
if %errorlevel% equ 0 (
    echo [INFO] ✓ GPU image is accessible
) else (
    echo [WARNING] GPU image requires authentication or doesn't exist
)

echo [INFO] Configuration complete!
echo.
echo Next steps:
echo 1. Edit .env.ghcr and add your GEMINI_API_KEY
echo 2. Use the GHCR images with:
echo    docker compose --env-file .env.ghcr -f docker-compose.ghcr.yml run --rm meeting-video-tool-cpu python -m src.main /input
echo.
echo Or use the main docker-compose.yml with GHCR images:
echo    docker compose --env-file .env.ghcr run --rm meeting-video-tool-cpu python -m src.main /input

pause