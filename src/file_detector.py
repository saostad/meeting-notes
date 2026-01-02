"""Simple file type detector."""

import subprocess
import json
from pathlib import Path
from typing import Dict, Any


class SimpleFileDetector:
    """Simple file type detector."""
    
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.aac', '.ogg'}
    VIDEO_EXTENSIONS = {'.mkv', '.mp4', '.avi', '.mov', '.webm'}
    
    @classmethod
    def detect_file_type(cls, file_path: str) -> str:
        """Detect if file is audio or video based on extension."""
        path = Path(file_path)
        suffix = path.suffix.lower()
        
        if suffix in cls.AUDIO_EXTENSIONS:
            return 'audio'
        elif suffix in cls.VIDEO_EXTENSIONS:
            return 'video'
        else:
            raise ValueError(f"Unsupported file format: {suffix}")
    
    @classmethod
    def validate_audio_file(cls, file_path: str) -> Dict[str, Any]:
        """Validate audio file has required properties for processing."""
        path = Path(file_path)
        
        # Ensure file exists and is audio type
        file_type = cls.detect_file_type(file_path)
        if file_type != 'audio':
            raise ValueError(f"File is not an audio file: {file_path}")
        
        # Try to validate with ffprobe first
        try:
            cmd = [
                'ffprobe',
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                '-show_streams',
                str(path)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=30
            )
            
            metadata = json.loads(result.stdout)
            
            # Check if file has audio streams
            audio_streams = [
                stream for stream in metadata.get('streams', [])
                if stream.get('codec_type') == 'audio'
            ]
            
            if not audio_streams:
                raise ValueError("No audio streams found in file")
            
            # Extract metadata
            format_info = metadata.get('format', {})
            primary_audio_stream = audio_streams[0]
            
            audio_metadata = {
                'file_path': file_path,
                'format_name': format_info.get('format_name', 'unknown'),
                'duration': float(format_info.get('duration', 0)),
                'size': int(format_info.get('size', 0)),
                'bit_rate': int(format_info.get('bit_rate', 0)),
                'audio_codec': primary_audio_stream.get('codec_name', 'unknown'),
                'sample_rate': int(primary_audio_stream.get('sample_rate', 0)),
                'channels': int(primary_audio_stream.get('channels', 0)),
                'audio_streams_count': len(audio_streams),
                'needs_conversion': False
            }
            
            return audio_metadata
            
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError) as e:
            # File validation failed - might need conversion
            print(f"⚠️  Audio file validation failed: {e}")
            print(f"   Attempting automatic format conversion...")
            
            # Return metadata indicating conversion is needed
            audio_metadata = {
                'file_path': file_path,
                'format_name': path.suffix.lower().lstrip('.'),
                'duration': 0,
                'size': path.stat().st_size,
                'bit_rate': 0,
                'audio_codec': 'unknown',
                'sample_rate': 0,
                'channels': 0,
                'audio_streams_count': 1,
                'needs_conversion': True,
                'conversion_reason': str(e)
            }
            
            return audio_metadata
    
    @classmethod
    def convert_audio_file(cls, input_path: str, output_path: str = None) -> str:
        """Convert audio file to a more compatible format (MP3).
        
        Args:
            input_path: Path to the input audio file
            output_path: Optional output path. If not provided, creates one based on input
            
        Returns:
            Path to the converted audio file
            
        Raises:
            RuntimeError: If conversion fails
        """
        input_file = Path(input_path)
        
        if output_path is None:
            # Create output path in same directory with _converted suffix
            output_path = input_file.parent / f"{input_file.stem}_converted.mp3"
        
        output_file = Path(output_path)
        
        # Skip conversion if output already exists and is newer
        if output_file.exists() and output_file.stat().st_mtime > input_file.stat().st_mtime:
            print(f"   ✓ Using existing converted file: {output_file}")
            return str(output_file)
        
        try:
            print(f"   🔄 Converting {input_file.name} to MP3...")
            
            cmd = [
                'ffmpeg',
                '-i', str(input_file),
                '-acodec', 'mp3',
                '-ab', '128k',  # 128kbps bitrate (good quality, reasonable size)
                '-ar', '44100',  # 44.1kHz sample rate (standard)
                '-ac', '2',      # Stereo (or mono if source is mono)
                '-y',            # Overwrite output file
                str(output_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=300  # 5 minute timeout for conversion
            )
            
            if output_file.exists() and output_file.stat().st_size > 0:
                print(f"   ✓ Conversion successful: {output_file}")
                return str(output_file)
            else:
                raise RuntimeError("Conversion completed but output file is empty or missing")
                
        except subprocess.CalledProcessError as e:
            error_msg = f"Audio conversion failed: {e.stderr.strip() if e.stderr else 'Unknown error'}"
            raise RuntimeError(error_msg)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Audio conversion timed out (file too large or system too slow)")
        except FileNotFoundError:
            raise RuntimeError("ffmpeg not found - required for audio conversion. Please install ffmpeg.")
        except Exception as e:
            raise RuntimeError(f"Unexpected error during audio conversion: {e}")