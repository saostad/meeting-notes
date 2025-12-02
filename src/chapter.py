"""Chapter data models for the Meeting Video Chapter Tool.

This module provides data structures for representing video chapters with
timestamps and titles, including validation and ffmpeg format conversion.
"""

from dataclasses import dataclass
from typing import List


@dataclass
class Chapter:
    """A video chapter with timestamp and title.
    
    Attributes:
        timestamp: Start time of the chapter in seconds from video start
        title: Descriptive title for the chapter
    """
    timestamp: float
    title: str
    
    def __post_init__(self):
        """Validate chapter data after initialization."""
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be non-negative, got {self.timestamp}")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        # Normalize title by stripping whitespace
        self.title = self.title.strip()
    
    def validate(self) -> bool:
        """Validate that the chapter has valid data.
        
        Returns:
            True if the chapter is valid
            
        Raises:
            ValueError: If validation fails
        """
        if self.timestamp < 0:
            raise ValueError(f"timestamp must be non-negative, got {self.timestamp}")
        if not self.title or not self.title.strip():
            raise ValueError("title must be a non-empty string")
        return True
    
    def to_ffmpeg_format(self) -> str:
        """Convert chapter to ffmpeg metadata format.
        
        Returns:
            String representation in ffmpeg chapter metadata format
            
        Example:
            >>> chapter = Chapter(timestamp=60.5, title="Introduction")
            >>> print(chapter.to_ffmpeg_format())
            [CHAPTER]
            TIMEBASE=1/1000
            START=60500
            END=60500
            title=Introduction
        """
        # Convert seconds to milliseconds for ffmpeg
        timestamp_ms = int(self.timestamp * 1000)
        
        return f"""[CHAPTER]
TIMEBASE=1/1000
START={timestamp_ms}
END={timestamp_ms}
title={self.title}"""


def validate_chapter_list(chapters: List[Chapter]) -> bool:
    """Validate that a list of chapters has valid structure.
    
    Checks that:
    - All chapters have non-negative timestamps
    - All chapters have non-empty titles
    - All timestamps are unique
    - Timestamps are in ascending order
    
    Args:
        chapters: List of Chapter objects to validate
        
    Returns:
        True if the chapter list is valid
        
    Raises:
        ValueError: If validation fails with details about the issue
    """
    if not chapters:
        raise ValueError("Chapter list cannot be empty")
    
    # Validate each chapter individually
    for i, chapter in enumerate(chapters):
        chapter.validate()
    
    # Check for unique timestamps
    timestamps = [c.timestamp for c in chapters]
    if len(timestamps) != len(set(timestamps)):
        raise ValueError("Chapter timestamps must be unique")
    
    # Check for ascending order
    if timestamps != sorted(timestamps):
        raise ValueError("Chapter timestamps must be in ascending order")
    
    return True
