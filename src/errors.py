"""
Custom exception classes and error formatting for the Meeting Video Chapter Tool.

This module provides structured error handling with contextual information
to help users understand and resolve issues during processing.
"""

from typing import Optional, Dict, Any


class MeetingVideoChapterError(Exception):
    """Base exception class for all Meeting Video Chapter Tool errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        """
        Initialize the error with a message and optional context.
        
        Args:
            message: Human-readable error description
            context: Additional contextual information (file paths, dependency names, etc.)
        """
        self.message = message
        self.context = context or {}
        super().__init__(self.format_error())
    
    def format_error(self) -> str:
        """Format the error message with context information."""
        return format_error_message(self.message, self.context)


class FileSystemError(MeetingVideoChapterError):
    """
    Exception raised for file system related errors.
    
    Examples:
        - Missing input files
        - Permission denied
        - Disk space issues
        - Invalid file formats
    """
    pass


class DependencyError(MeetingVideoChapterError):
    """
    Exception raised for external dependency errors.
    
    Examples:
        - ffmpeg not found or execution failure
        - Whisper model loading failure
        - Gemini API errors (network, authentication, rate limits)
    """
    pass


class ValidationError(MeetingVideoChapterError):
    """
    Exception raised for data validation errors.
    
    Examples:
        - Empty or malformed transcripts
        - Invalid chapter data
        - Configuration validation failures
    """
    pass


class ProcessingError(MeetingVideoChapterError):
    """
    Exception raised for processing failures.
    
    Examples:
        - Audio extraction failures
        - Transcription failures
        - Chapter identification failures
        - Chapter merging failures
    """
    pass


def format_error_message(message: str, context: Dict[str, Any]) -> str:
    """
    Format an error message with contextual information.
    
    This function creates user-friendly error messages that include relevant
    context such as file paths, dependency names, and operation names.
    
    Args:
        message: The main error message
        context: Dictionary containing contextual information
            - file_path: Path to the file involved in the error
            - dependency: Name of the external dependency that failed
            - operation: Name of the operation that failed
            - cause: Original error message from external tool
            - Any other relevant key-value pairs
    
    Returns:
        Formatted error message string with context
    
    Example:
        >>> format_error_message(
        ...     "Audio extraction failed",
        ...     {"file_path": "/path/to/video.mkv", "dependency": "ffmpeg", "cause": "No audio track"}
        ... )
        'Error: Audio extraction failed\\n  File: /path/to/video.mkv\\n  Tool: ffmpeg\\n  Cause: No audio track'
    """
    lines = [f"Error: {message}"]
    
    # Add file path if present
    if "file_path" in context:
        lines.append(f"  File: {context['file_path']}")
    
    # Add dependency/tool name if present
    if "dependency" in context:
        lines.append(f"  Tool: {context['dependency']}")
    
    # Add operation name if present
    if "operation" in context:
        lines.append(f"  Operation: {context['operation']}")
    
    # Add cause/original error if present
    if "cause" in context:
        lines.append(f"  Cause: {context['cause']}")
    
    # Add any other context information
    for key, value in context.items():
        if key not in ["file_path", "dependency", "operation", "cause"]:
            # Format key as title case with spaces
            formatted_key = key.replace("_", " ").title()
            lines.append(f"  {formatted_key}: {value}")
    
    return "\n".join(lines)
