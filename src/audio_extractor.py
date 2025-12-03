"""Audio extraction component for the Meeting Video Chapter Tool.

This module provides functionality to extract audio tracks from MKV video files
using ffmpeg, with validation and error handling.
"""

import os
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from src.errors import FileSystemError, DependencyError, ProcessingError


class AudioExtractor:
    """Extracts audio tracks from MKV video files to MP3 format.
    
    This class wraps ffmpeg to extract audio from video files while ensuring
    proper validation and error handling. Original files are preserved on failure.
    """
    
    def __init__(self):
        """Initialize the AudioExtractor and verify ffmpeg is available."""
        self._verify_ffmpeg()
        self._gpu_available = self._check_gpu_support()
    
    def _verify_ffmpeg(self) -> None:
        """Verify that ffmpeg is installed and accessible.
        
        Raises:
            DependencyError: If ffmpeg is not found in system PATH
        """
        if not shutil.which("ffmpeg"):
            raise DependencyError(
                "ffmpeg not found in system PATH",
                context={
                    "dependency": "ffmpeg",
                    "operation": "initialization",
                    "cause": "ffmpeg must be installed and available in PATH"
                }
            )
    
    def _check_gpu_support(self) -> bool:
        """Check if ffmpeg has GPU hardware acceleration support.
        
        Returns:
            True if GPU acceleration is available, False otherwise
        """
        try:
            # Check for NVIDIA NVDEC support
            result = subprocess.run(
                ["ffmpeg", "-hwaccels"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if cuda is in the list of hardware accelerators
            return "cuda" in result.stdout.lower()
        
        except Exception:
            return False
    
    def validate_mkv(self, mkv_path: str) -> bool:
        """Validate that the MKV file exists and contains an audio track.
        
        Args:
            mkv_path: Path to the MKV file
            
        Returns:
            True if the file is valid and contains audio
            
        Raises:
            FileSystemError: If the file doesn't exist or is not accessible
            ValidationError: If the file has no audio track
        """
        mkv_file = Path(mkv_path)
        
        # Check file existence
        if not mkv_file.exists():
            raise FileSystemError(
                "MKV file does not exist",
                context={
                    "file_path": str(mkv_path),
                    "operation": "validation"
                }
            )
        
        # Check if it's a file (not a directory)
        if not mkv_file.is_file():
            raise FileSystemError(
                "Path is not a file",
                context={
                    "file_path": str(mkv_path),
                    "operation": "validation"
                }
            )
        
        # Check for audio track using ffprobe
        if not self._has_audio_track(mkv_path):
            raise ProcessingError(
                "MKV file contains no audio track",
                context={
                    "file_path": str(mkv_path),
                    "dependency": "ffmpeg",
                    "operation": "audio track detection"
                }
            )
        
        return True
    
    def _has_audio_track(self, mkv_path: str) -> bool:
        """Check if the MKV file has an audio track using ffprobe.
        
        Args:
            mkv_path: Path to the MKV file
            
        Returns:
            True if audio track is present, False otherwise
        """
        try:
            # Use ffprobe to check for audio streams
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-select_streams", "a:0",
                    "-show_entries", "stream=codec_type",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    mkv_path
                ],
                capture_output=True,
                text=True,
                check=False
            )
            
            # If output contains "audio", an audio track exists
            return "audio" in result.stdout.lower()
        
        except Exception as e:
            # If ffprobe fails, we can't determine audio presence
            raise DependencyError(
                "Failed to check for audio track",
                context={
                    "file_path": str(mkv_path),
                    "dependency": "ffprobe",
                    "operation": "audio track detection",
                    "cause": str(e)
                }
            )
    
    def extract(self, mkv_path: str, output_path: Optional[str] = None) -> str:
        """Extract audio from MKV file to MP3 format.
        
        Args:
            mkv_path: Path to the input MKV file
            output_path: Optional path for the output MP3 file.
                        If not provided, saves to same directory as input with .mp3 extension
        
        Returns:
            Path to the extracted MP3 file
            
        Raises:
            FileSystemError: If input file doesn't exist or is not accessible
            ProcessingError: If audio extraction fails
            DependencyError: If ffmpeg is not available or fails
        """
        # Validate the input file
        self.validate_mkv(mkv_path)
        
        # Determine output path
        if output_path is None:
            mkv_file = Path(mkv_path)
            output_path = str(mkv_file.parent / f"{mkv_file.stem}.mp3")
        
        output_file = Path(output_path)
        
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use a temporary file to ensure atomicity
        temp_output = output_file.parent / f"{output_file.stem}.tmp.mp3"
        
        try:
            # Build ffmpeg command with GPU acceleration if available
            ffmpeg_cmd = ["ffmpeg"]
            
            # Add GPU hardware acceleration for decoding if available
            if self._gpu_available:
                ffmpeg_cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
            
            ffmpeg_cmd.extend([
                "-i", mkv_path,
                "-vn",  # No video
                "-acodec", "libmp3lame",  # MP3 codec
                "-q:a", "2",  # High quality
                "-y",  # Overwrite output file
                str(temp_output)
            ])
            
            # Extract audio using ffmpeg
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if ffmpeg succeeded
            if result.returncode != 0:
                raise ProcessingError(
                    "Audio extraction failed",
                    context={
                        "file_path": str(mkv_path),
                        "dependency": "ffmpeg",
                        "operation": "audio extraction",
                        "cause": result.stderr.strip() if result.stderr else "Unknown error"
                    }
                )
            
            # Verify the output file was created and has content
            if not temp_output.exists() or temp_output.stat().st_size == 0:
                raise ProcessingError(
                    "Audio extraction produced empty or missing file",
                    context={
                        "file_path": str(mkv_path),
                        "output_path": str(output_path),
                        "operation": "audio extraction"
                    }
                )
            
            # Move temp file to final location (atomic operation)
            temp_output.replace(output_file)
            
            return str(output_file)
        
        except (FileSystemError, ProcessingError, DependencyError):
            # Clean up temp file if it exists
            if temp_output.exists():
                try:
                    temp_output.unlink()
                except Exception:
                    pass  # Best effort cleanup
            raise
        
        except Exception as e:
            # Clean up temp file if it exists
            if temp_output.exists():
                try:
                    temp_output.unlink()
                except Exception:
                    pass  # Best effort cleanup
            
            raise ProcessingError(
                "Unexpected error during audio extraction",
                context={
                    "file_path": str(mkv_path),
                    "operation": "audio extraction",
                    "cause": str(e)
                }
            )
