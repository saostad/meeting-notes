# Meeting Video Chapter Tool

Automatically add navigable chapter markers to meeting video files using AI-powered transcription and analysis.

## Overview

The Meeting Video Chapter Tool processes MKV video files from recorded meetings, transcribes the audio content using OpenAI's Whisper model, identifies logical chapter boundaries using Google's Gemini model, and adds chapter markers to the video files for easy navigation.

## Features

- **Automatic Audio Extraction**: Extracts audio from MKV files using ffmpeg
- **AI Transcription**: Transcribes audio using Whisper large-v3-turbo model
- **Intelligent Chapter Detection**: Identifies logical chapter boundaries using Gemini AI
- **Chapter Embedding**: Adds chapter markers directly to video files
- **Pipeline Processing**: Complete end-to-end processing with a single command
- **Skip Existing Files**: Optionally reuse intermediate files from previous runs
- **Clear Error Messages**: Detailed error reporting with context

## Prerequisites

### System Requirements

- Python 3.8 or higher
- ffmpeg 4.0 or higher (must be in system PATH)
- 4GB+ RAM (8GB+ recommended for faster processing)
- GPU with CUDA support (optional, but recommended for faster transcription)

### External Dependencies

**ffmpeg** must be installed and available in your system PATH:

- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg` (Ubuntu/Debian) or `sudo yum install ffmpeg` (RHEL/CentOS)

Verify installation:
```bash
ffmpeg -version
```

## Installation

### 1. Clone or Download the Repository

```bash
git clone <repository-url>
cd meeting-video-chapters
```

### 2. Create a Virtual Environment (Recommended)

```bash
python -m venv venv
```

Activate the virtual environment:
- **Windows**: `venv\Scripts\activate`
- **macOS/Linux**: `source venv/bin/activate`

### 3. Install Python Dependencies

**For CPU-only (slower transcription):**
```bash
pip install -r requirements.txt
```

**For NVIDIA GPU with CUDA 11.8:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt
```

**For NVIDIA GPU with CUDA 12.1:**
```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

See [GPU_SETUP.md](GPU_SETUP.md) for detailed GPU configuration instructions.

### 4. Configure API Keys

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:
```env
GEMINI_API_KEY=your_actual_api_key_here
```

**Getting a Gemini API Key:**
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click "Create API Key"
4. Copy the key and paste it into your `.env` file

## Configuration

### Environment Variables

Configuration is loaded from the `.env` file or environment variables. Environment variables take precedence over `.env` file values.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | **Yes** | - | API key for Google Gemini |
| `GEMINI_MODEL` | No | `gemini-flash-latest` | Gemini model to use for chapter identification |
| `WHISPER_MODEL` | No | `openai/whisper-large-v3-turbo` | Whisper model to use for transcription |
| `OUTPUT_DIR` | No | Same as input file | Directory where generated files will be saved |
| `SKIP_EXISTING` | No | `false` | Skip regenerating files that already exist |

### Example .env File

```env
# Required: Get your API key from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=AIzaSyD...your_key_here

# Optional: Model configuration
GEMINI_MODEL=gemini-flash-latest
WHISPER_MODEL=openai/whisper-large-v3-turbo

# Optional: Output configuration
OUTPUT_DIR=./output
SKIP_EXISTING=false
```

## Usage

### Basic Usage

Process a meeting video file:
```bash
python src/main.py meeting.mkv
```

This will:
1. Extract audio from `meeting.mkv` → `meeting.mp3`
2. Transcribe audio → `meeting_transcript.json`
3. Identify chapters using AI
4. Create chaptered video → `meeting_chaptered.mkv`
5. Generate subtitles → `meeting_chaptered.srt`

### Command-Line Options

```bash
python src/main.py [OPTIONS] INPUT_FILE
```

**Arguments:**
- `INPUT_FILE`: Path to the input MKV video file (required)

**Options:**
- `-o, --output-dir DIR`: Directory where generated files will be saved (default: same as input file)
- `-s, --skip-existing`: Skip regenerating intermediate files if they already exist
- `--env-file PATH`: Path to .env file (default: .env)
- `-h, --help`: Show help message

### Usage Examples

**Process with custom output directory:**
```bash
python src/main.py meeting.mkv --output-dir ./processed
```

**Skip existing intermediate files:**
```bash
python src/main.py meeting.mkv --skip-existing
```

**Combine options:**
```bash
python src/main.py meeting.mkv -o ./output -s
```

**Use custom .env file:**
```bash
python src/main.py meeting.mkv --env-file .env.production
```

### Output Files

For an input file `meeting.mkv`, the tool generates:

- `meeting.mp3` - Extracted audio
- `meeting_transcript.json` - Timestamped transcript (JSON format)
- `meeting_chaptered.srt` - Subtitle file (SRT format)
- `meeting_chaptered.mkv` - Final video with embedded chapters

All files are saved to the same directory as the input file, unless `--output-dir` is specified.

**Note:** The subtitle file (`.srt`) has the same base name as the chaptered video file, so VLC and most video players will automatically load and display the subtitles when you open the video.

## Viewing Chapters and Subtitles

Once processing is complete, you can view and navigate chapters and subtitles in video players:

### VLC Media Player

**Chapters:**
1. Open the chaptered MKV file
2. Go to **Playback** → **Chapter** to see the chapter list
3. Click a chapter to jump to that section

**Subtitles:**
- VLC automatically loads the `.srt` file if it's in the same directory with the same base name
- If subtitles don't appear, go to **Subtitle** → **Add Subtitle File** and select the `.srt` file
- Toggle subtitles on/off with the **V** key

### mpv

**Chapters:**
1. Open the chaptered MKV file: `mpv meeting_chaptered.mkv`
2. Press `Shift+O` to show the chapter list
3. Use `PgUp`/`PgDn` to navigate between chapters

**Subtitles:**
- mpv automatically loads the `.srt` file if it's in the same directory
- Toggle subtitles on/off with the **V** key
- Cycle through subtitle tracks with **J**

### Other Players
Most modern video players support both MKV chapter navigation and SRT subtitles. The subtitle file will be automatically loaded if it has the same name as the video file and is in the same directory.

## Troubleshooting

### Common Issues

#### "Error: Missing required API key: GEMINI_API_KEY"

**Cause**: The Gemini API key is not configured.

**Solution**:
1. Create a `.env` file in the project root (copy from `.env.example`)
2. Add your API key: `GEMINI_API_KEY=your_actual_key_here`
3. Get a key from [Google AI Studio](https://makersuite.google.com/app/apikey)

#### "Error: ffmpeg not found"

**Cause**: ffmpeg is not installed or not in system PATH.

**Solution**:
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html), extract, and add to PATH
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`

Verify: `ffmpeg -version`

#### "Error: No audio track found in video file"

**Cause**: The MKV file doesn't contain an audio track.

**Solution**:
- Verify the file has audio by playing it in a media player
- Check if the file is corrupted
- Try re-recording or re-downloading the file

#### Transcription is Very Slow

**Cause**: Running on CPU instead of GPU.

**Solution**:
1. Install CUDA-enabled PyTorch (see Installation section)
2. Verify GPU is detected: `python -c "import torch; print(torch.cuda.is_available())"`
3. See [GPU_SETUP.md](GPU_SETUP.md) for detailed GPU configuration

#### "Error: Gemini API rate limit exceeded"

**Cause**: Too many API requests in a short time.

**Solution**:
- Wait a few minutes and try again
- Check your API quota at [Google AI Studio](https://makersuite.google.com/app/apikey)
- Consider upgrading your API plan if you need higher limits

#### "Error: Failed to load model weights"

**Cause**: Whisper model download failed or insufficient disk space.

**Solution**:
1. Check internet connection
2. Ensure you have ~2GB free disk space for model weights
3. Delete cached models and retry: `rm -rf ~/.cache/huggingface/`
4. Try a smaller model: Set `WHISPER_MODEL=openai/whisper-base` in `.env`

#### Chapters Not Appearing in Video Player

**Cause**: Video player doesn't support MKV chapters or file is corrupted.

**Solution**:
- Try a different player (VLC, mpv, or MPC-HC)
- Verify chapters were embedded: `ffmpeg -i meeting_chaptered.mkv` (look for "Chapter" entries)
- Re-run the tool without `--skip-existing` to regenerate the file

#### Subtitles Not Appearing in Video Player

**Cause**: Subtitle file not found or player doesn't auto-load subtitles.

**Solution**:
- Verify the `.srt` file exists in the same directory as the video
- Ensure the subtitle file has the same base name as the video (e.g., `meeting_chaptered.mkv` and `meeting_chaptered.srt`)
- Manually load subtitles in your player:
  - **VLC**: Subtitle → Add Subtitle File
  - **mpv**: Use `--sub-file=meeting_chaptered.srt` flag
- Check subtitle encoding: the file should be UTF-8 encoded

#### "Permission Denied" Errors

**Cause**: Insufficient permissions to read input file or write output files.

**Solution**:
- Check file permissions: `ls -l meeting.mkv`
- Ensure output directory is writable
- On Windows, run as administrator if necessary
- Move files to a directory where you have write permissions

### Getting Help

If you encounter issues not covered here:

1. Check the error message carefully - it includes context about what failed
2. Verify all prerequisites are installed correctly
3. Try with a small test video file first
4. Check the generated intermediate files for clues
5. Review the configuration in your `.env` file

## Performance Notes

### Processing Time

Typical processing times for a 1-hour meeting video:

- **Audio Extraction**: 10-30 seconds
- **Transcription** (CPU): 30-60 minutes
- **Transcription** (GPU): 5-10 minutes
- **Chapter Identification**: 5-10 seconds
- **Chapter Merging**: 10-30 seconds

**Total**: ~5-15 minutes with GPU, ~30-60 minutes with CPU

### Optimization Tips

1. **Use GPU**: Install CUDA-enabled PyTorch for 5-10x faster transcription
2. **Skip Existing Files**: Use `--skip-existing` when re-running to reuse transcripts
3. **Smaller Model**: Use `WHISPER_MODEL=openai/whisper-medium` for faster (but less accurate) transcription
4. **Batch Processing**: Process multiple files sequentially to reuse loaded models

## Project Structure

```
meeting-video-chapters/
├── src/
│   ├── main.py                    # CLI entry point
│   ├── config.py                  # Configuration management
│   ├── pipeline.py                # Pipeline orchestration
│   ├── audio_extractor.py         # Audio extraction component
│   ├── transcription_service.py   # Whisper transcription
│   ├── chapter_analyzer.py        # Gemini chapter identification
│   ├── chapter_merger.py          # Chapter embedding
│   ├── transcript.py              # Transcript data model
│   ├── chapter.py                 # Chapter data model
│   └── errors.py                  # Error handling
├── tests/                         # Unit and property tests
├── config/                        # Configuration files
├── output/                        # Default output directory
├── .env                           # Environment configuration (create from .env.example)
├── .env.example                   # Example environment file
├── requirements.txt               # Python dependencies
├── GPU_SETUP.md                   # GPU configuration guide
└── README.md                      # This file
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_config.py

# Run property-based tests
pytest tests/ -k property
```

### Code Structure

The tool follows a modular pipeline architecture:

1. **AudioExtractor**: Wraps ffmpeg for audio extraction
2. **TranscriptionService**: Interfaces with Whisper model
3. **ChapterAnalyzer**: Uses Gemini API for chapter identification
4. **ChapterMerger**: Wraps ffmpeg for chapter embedding
5. **Pipeline**: Orchestrates the complete workflow

Each component can be used independently or as part of the full pipeline.

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [Google Gemini](https://ai.google.dev/) for chapter identification
- [ffmpeg](https://ffmpeg.org/) for audio/video processing
