# GPU Setup for Meeting Video Chapter Tool

## Why GPU Acceleration?

The Whisper transcription model runs significantly faster on GPU. For a 10-minute audio file:
- **CPU**: 5-15 minutes
- **GPU**: 30 seconds - 2 minutes

## Requirements

- NVIDIA GPU with CUDA support
- CUDA Toolkit installed (11.8 or 12.1)

## Installation Steps

### 1. Check if you have an NVIDIA GPU

```bash
nvidia-smi
```

If this command works, you have an NVIDIA GPU.

### 2. Uninstall CPU-only PyTorch (if installed)

```bash
pip uninstall torch torchvision torchaudio -y
```

### 3. Install GPU-enabled PyTorch

**For CUDA 11.8:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**For CUDA 12.1:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### 4. Verify GPU is detected

```python
import torch
print("CUDA available:", torch.cuda.is_available())
print("CUDA device:", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A")
```

## Troubleshooting

### "CUDA available: False"

1. Make sure you have an NVIDIA GPU
2. Install CUDA Toolkit from: https://developer.nvidia.com/cuda-downloads
3. Reinstall PyTorch with the correct CUDA version
4. Restart your terminal/IDE

### Out of Memory Errors

If you get CUDA out of memory errors, the model is too large for your GPU. The system will automatically fall back to CPU.

## Performance Tips

- Close other GPU-intensive applications
- Use the turbo model (`whisper-large-v3-turbo`) for faster processing
- For very long audio files (>1 hour), consider splitting them into chunks
