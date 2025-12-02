"""Chapter merging component for the Meeting Video Chapter Tool.

This module provides functionality to embed chapter metadata into MKV video files
using ffmpeg, with validation and error handling.
"""

import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import List, Optional

from src.chapter import Chapter, validate_chapter_list
from src.errors import FileSystemError, DependencyError, ProcessingError, ValidationError


class ChapterMerger:
    """Embeds chapter metadata into MKV video files.
    
    This class wraps ffmpeg to merge chapter markers into video files while ensuring
    proper validation and error handling. Original files are preserved on failure.
    """
    
    def __init__(self):
        """Initialize the ChapterMerger and verify ffmpeg is available."""
        self._verify_ffmpeg()
    
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
    
    def validate_chapters(self, chapters: List[Chapter]) -> bool:
        """Validate that the chapter list has valid structure.
        
        Args:
            chapters: List of Chapter objects to validate
            
        Returns:
            True if the chapter list is valid
            
        Raises:
            ValidationError: If validation fails with details about the issue
        """
        try:
            return validate_chapter_list(chapters)
        except ValueError as e:
            raise ValidationError(
                "Chapter validation failed",
                context={
                    "operation": "chapter validation",
                    "cause": str(e)
                }
            )
    
    def create_metadata_file(self, chapters: List[Chapter]) -> str:
        """Generate ffmpeg metadata file from chapter list.
        
        Creates a temporary file containing chapter metadata in ffmpeg format.
        The caller is responsible for cleaning up the temporary file.
        
        Args:
            chapters: List of Chapter objects to convert
            
        Returns:
            Path to the temporary metadata file
            
        Raises:
            ValidationError: If chapter list is invalid
            FileSystemError: If metadata file cannot be created
        """
        # Validate chapters first
        self.validate_chapters(chapters)
        
        try:
            # Create temporary file for metadata
            fd, metadata_path = tempfile.mkstemp(suffix='.txt', prefix='chapters_')
            
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                # Write ffmpeg metadata header
                f.write(";FFMETADATA1\n")
                
                # Write each chapter
                for i, chapter in enumerate(chapters):
                    # For the END time, use the next chapter's start or the current start
                    # (ffmpeg will extend to the end of the video automatically)
                    start_ms = int(chapter.timestamp * 1000)
                    if i + 1 < len(chapters):
                        end_ms = int(chapters[i + 1].timestamp * 1000)
                    else:
                        # For the last chapter, use a very large value
                        # ffmpeg will adjust this to the actual video duration
                        end_ms = start_ms
                    
                    f.write("\n[CHAPTER]\n")
                    f.write("TIMEBASE=1/1000\n")
                    f.write(f"START={start_ms}\n")
                    f.write(f"END={end_ms}\n")
                    f.write(f"title={chapter.title}\n")
            
            return metadata_path
        
        except Exception as e:
            raise FileSystemError(
                "Failed to create metadata file",
                context={
                    "operation": "metadata file creation",
                    "cause": str(e)
                }
            )
    
    def merge(self, mkv_path: str, chapters: List[Chapter], output_path: Optional[str] = None) -> str:
        """Embed chapter metadata into MKV file.
        
        Args:
            mkv_path: Path to the input MKV file
            chapters: List of Chapter objects to embed
            output_path: Optional path for the output MKV file.
                        If not provided, saves to same directory with '_chaptered' suffix
        
        Returns:
            Path to the output MKV file with embedded chapters
            
        Raises:
            FileSystemError: If input file doesn't exist or is not accessible
            ValidationError: If chapter list is invalid
            ProcessingError: If chapter merging fails
            DependencyError: If ffmpeg is not available or fails
        """
        # Validate input file exists
        mkv_file = Path(mkv_path)
        if not mkv_file.exists():
            raise FileSystemError(
                "MKV file does not exist",
                context={
                    "file_path": str(mkv_path),
                    "operation": "chapter merging"
                }
            )
        
        if not mkv_file.is_file():
            raise FileSystemError(
                "Path is not a file",
                context={
                    "file_path": str(mkv_path),
                    "operation": "chapter merging"
                }
            )
        
        # Validate chapters
        self.validate_chapters(chapters)
        
        # Determine output path
        if output_path is None:
            output_path = str(mkv_file.parent / f"{mkv_file.stem}_chaptered.mkv")
        
        output_file = Path(output_path)
        
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Use a temporary file to ensure atomicity
        temp_output = output_file.parent / f"{output_file.stem}.tmp.mkv"
        
        # Create metadata file
        metadata_path = None
        
        try:
            # Generate metadata file
            metadata_path = self.create_metadata_file(chapters)
            
            # Merge chapters using ffmpeg
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i", str(mkv_path),
                    "-i", metadata_path,
                    "-map_metadata", "1",
                    "-codec", "copy",
                    "-y",  # Overwrite output file
                    str(temp_output)
                ],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Check if ffmpeg succeeded
            if result.returncode != 0:
                raise ProcessingError(
                    "Chapter merging failed",
                    context={
                        "file_path": str(mkv_path),
                        "dependency": "ffmpeg",
                        "operation": "chapter merging",
                        "cause": result.stderr.strip() if result.stderr else "Unknown error"
                    }
                )
            
            # Verify the output file was created and has content
            if not temp_output.exists() or temp_output.stat().st_size == 0:
                raise ProcessingError(
                    "Chapter merging produced empty or missing file",
                    context={
                        "file_path": str(mkv_path),
                        "output_path": str(output_path),
                        "operation": "chapter merging"
                    }
                )
            
            # Move temp file to final location (atomic operation)
            temp_output.replace(output_file)
            
            return str(output_file)
        
        except (FileSystemError, ValidationError, ProcessingError, DependencyError):
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
                "Unexpected error during chapter merging",
                context={
                    "file_path": str(mkv_path),
                    "operation": "chapter merging",
                    "cause": str(e)
                }
            )
        
        finally:
            # Clean up metadata file
            if metadata_path and os.path.exists(metadata_path):
                try:
                    os.unlink(metadata_path)
                except Exception:
                    pass  # Best effort cleanup
