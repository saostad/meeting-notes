# Use official NVIDIA CUDA base image for proper GPU support
FROM nvidia/cuda:13.0.2-cudnn-devel-ubuntu24.04

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set NVIDIA environment variables for GPU acceleration (required for video encoding/decoding)
ENV \
  NVIDIA_DRIVER_CAPABILITIES="compute,video,utility" \
  NVIDIA_VISIBLE_DEVICES="all"

# Install Python 3.12 and system dependencies
RUN apt-get update && apt-get install -y \
    software-properties-common \
    wget \
    curl \
    xz-utils \
    jq \
    && add-apt-repository ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    python3.12-venv \
    python3-pip \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install build dependencies for ffmpeg compilation
RUN apt-get update && apt-get install -y \
    autoconf \
    automake \
    build-essential \
    cmake \
    git \
    libass-dev \
    libfreetype6-dev \
    libfontconfig1-dev \
    libfribidi-dev \
    libharfbuzz-dev \
    libgnutls28-dev \
    libmp3lame-dev \
    libsdl2-dev \
    libtool \
    libva-dev \
    libvdpau-dev \
    libvorbis-dev \
    libxcb1-dev \
    libxcb-shm0-dev \
    libxcb-xfixes0-dev \
    meson \
    ninja-build \
    pkg-config \
    texinfo \
    yasm \
    zlib1g-dev \
    nasm \
    libx264-dev \
    libx265-dev \
    libnuma-dev \
    libvpx-dev \
    libfdk-aac-dev \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

# Install NVIDIA codec headers for GPU acceleration
RUN cd /tmp && \
    git clone --depth 1 --branch n13.0.19.0 https://github.com/FFmpeg/nv-codec-headers.git && \
    cd nv-codec-headers && \
    make install && \
    cd / && rm -rf /tmp/nv-codec-headers

# Download and compile ffmpeg 8.0.1 with NVIDIA GPU support and text filters
RUN cd /tmp && \
    wget https://ffmpeg.org/releases/ffmpeg-8.0.1.tar.xz && \
    tar -xf ffmpeg-8.0.1.tar.xz && \
    cd ffmpeg-8.0.1 && \
    PKG_CONFIG_PATH="/usr/local/lib/pkgconfig:/usr/lib/x86_64-linux-gnu/pkgconfig" \
    ./configure \
      --prefix=/usr/local \
      --enable-gpl \
      --enable-nonfree \
      --enable-libass \
      --enable-libfdk-aac \
      --enable-libfreetype \
      --enable-libfontconfig \
      --enable-libfribidi \
      --enable-libharfbuzz \
      --enable-libmp3lame \
      --enable-libopus \
      --enable-libvorbis \
      --enable-libvpx \
      --enable-libx264 \
      --enable-libx265 \
      --enable-nvenc \
      --enable-nvdec \
      --enable-cuvid \
      --enable-vaapi \
      --enable-vdpau \
      --enable-filter=drawtext && \
    make -j$(nproc) && \
    make install && \
    ldconfig && \
    cd / && rm -rf /tmp/ffmpeg-8.0.1*

# Install Ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# Verify ffmpeg version, GPU support, and drawtext filter
RUN ffmpeg -version && ffmpeg -hwaccels && ffmpeg -filters | grep drawtext

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1 \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Create a virtual environment for Python 3.12 to avoid externally managed environment issues
RUN python3.12 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code and setup script
COPY src/ ./src/
COPY requirements.txt ./
COPY setup.sh ./
COPY .env.example ./.env.example

# Make setup script executable
RUN chmod +x setup.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV OLLAMA_MODELS=/workspace/models/ollama

# Use setup script as entrypoint for runtime dependency management
ENTRYPOINT ["./setup.sh"]