"""Transcript data models for the Meeting Video Chapter Tool.

This module provides data structures for representing transcripts with
timestamped segments, including serialization and deserialization capabilities.
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import List


@dataclass
class TranscriptSegment:
    """A single segment of transcribed audio with timing information.
    
    Attributes:
        start_time: Start time of the segment in seconds
        end_time: End time of the segment in seconds
        text: Transcribed text content for this segment
    """
    start_time: float
    end_time: float
    text: str
    
    def __post_init__(self):
        """Validate segment data after initialization."""
        if self.start_time < 0:
            raise ValueError(f"start_time must be non-negative, got {self.start_time}")
        if self.end_time < 0:
            raise ValueError(f"end_time must be non-negative, got {self.end_time}")
        if self.end_time < self.start_time:
            raise ValueError(
                f"end_time ({self.end_time}) must be >= start_time ({self.start_time})"
            )


@dataclass
class Transcript:
    """Complete transcript with segments and metadata.
    
    Attributes:
        segments: List of transcript segments with timing information
        full_text: Complete transcribed text (all segments concatenated)
        duration: Total duration of the audio in seconds
    """
    segments: List[TranscriptSegment]
    full_text: str
    duration: float
    
    def __post_init__(self):
        """Validate transcript data after initialization."""
        if self.duration < 0:
            raise ValueError(f"duration must be non-negative, got {self.duration}")
    
    def to_file(self, path: str) -> None:
        """Save transcript to a JSON file.
        
        Args:
            path: Path where the transcript file should be saved
            
        Raises:
            IOError: If the file cannot be written
        """
        output_path = Path(path)
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dictionary format
        data = {
            "segments": [
                {
                    "start_time": seg.start_time,
                    "end_time": seg.end_time,
                    "text": seg.text
                }
                for seg in self.segments
            ],
            "full_text": self.full_text,
            "duration": self.duration
        }
        
        # Write to file with pretty formatting
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def to_srt(self, path: str) -> None:
        """Save transcript as an SRT subtitle file.
        
        SRT (SubRip) format is widely supported by video players like VLC.
        The file will be automatically loaded if it has the same name as the video.
        
        Args:
            path: Path where the SRT file should be saved
            
        Raises:
            IOError: If the file cannot be written
        """
        output_path = Path(path)
        
        # Create parent directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate SRT content
        srt_content = []
        for i, segment in enumerate(self.segments, start=1):
            # Format timestamps as HH:MM:SS,mmm
            start_time = self._format_srt_timestamp(segment.start_time)
            end_time = self._format_srt_timestamp(segment.end_time)
            
            # SRT format:
            # 1
            # 00:00:00,000 --> 00:00:05,000
            # Subtitle text
            # (blank line)
            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(segment.text.strip())
            srt_content.append("")  # Blank line between subtitles
        
        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(srt_content))
    
    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        """Format a timestamp in seconds to SRT format (HH:MM:SS,mmm).
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted timestamp string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"
    
    @classmethod
    def from_file(cls, path: str) -> "Transcript":
        """Load transcript from a JSON file.
        
        Args:
            path: Path to the transcript file
            
        Returns:
            Transcript: Loaded transcript object
            
        Raises:
            FileNotFoundError: If the file doesn't exist
            ValueError: If the file format is invalid
            IOError: If the file cannot be read
        """
        input_path = Path(path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {path}")
        
        if not input_path.is_file():
            raise ValueError(f"Path is not a file: {path}")
        
        # Read and parse JSON
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Validate required fields
        if "segments" not in data:
            raise ValueError("Invalid transcript file: missing 'segments' field")
        if "full_text" not in data:
            raise ValueError("Invalid transcript file: missing 'full_text' field")
        if "duration" not in data:
            raise ValueError("Invalid transcript file: missing 'duration' field")
        
        # Convert segments to TranscriptSegment objects
        segments = [
            TranscriptSegment(
                start_time=seg["start_time"],
                end_time=seg["end_time"],
                text=seg["text"]
            )
            for seg in data["segments"]
        ]
        
        return cls(
            segments=segments,
            full_text=data["full_text"],
            duration=data["duration"]
        )
