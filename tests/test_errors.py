"""
Unit tests for error handling infrastructure.
"""

import pytest
from src.errors import (
    MeetingVideoChapterError,
    FileSystemError,
    DependencyError,
    ValidationError,
    ProcessingError,
    format_error_message
)


class TestErrorFormatting:
    """Test error message formatting with context."""
    
    def test_format_error_with_file_path(self):
        """Test error formatting includes file path."""
        message = "File not found"
        context = {"file_path": "/path/to/file.mkv"}
        result = format_error_message(message, context)
        
        assert "Error: File not found" in result
        assert "File: /path/to/file.mkv" in result
    
    def test_format_error_with_dependency(self):
        """Test error formatting includes dependency name."""
        message = "External tool failed"
        context = {"dependency": "ffmpeg"}
        result = format_error_message(message, context)
        
        assert "Error: External tool failed" in result
        assert "Tool: ffmpeg" in result
    
    def test_format_error_with_operation(self):
        """Test error formatting includes operation name."""
        message = "Operation failed"
        context = {"operation": "audio_extraction"}
        result = format_error_message(message, context)
        
        assert "Error: Operation failed" in result
        assert "Operation: audio_extraction" in result
    
    def test_format_error_with_cause(self):
        """Test error formatting includes original cause."""
        message = "Processing failed"
        context = {"cause": "No audio track found"}
        result = format_error_message(message, context)
        
        assert "Error: Processing failed" in result
        assert "Cause: No audio track found" in result
    
    def test_format_error_with_all_context(self):
        """Test error formatting with all context fields."""
        message = "Audio extraction failed"
        context = {
            "file_path": "/path/to/meeting.mkv",
            "dependency": "ffmpeg",
            "operation": "extract_audio",
            "cause": "No audio track found in video file"
        }
        result = format_error_message(message, context)
        
        assert "Error: Audio extraction failed" in result
        assert "File: /path/to/meeting.mkv" in result
        assert "Tool: ffmpeg" in result
        assert "Operation: extract_audio" in result
        assert "Cause: No audio track found in video file" in result
    
    def test_format_error_with_custom_context(self):
        """Test error formatting with custom context fields."""
        message = "API error"
        context = {
            "api_key": "missing",
            "retry_count": 3
        }
        result = format_error_message(message, context)
        
        assert "Error: API error" in result
        assert "Api Key: missing" in result
        assert "Retry Count: 3" in result
    
    def test_format_error_empty_context(self):
        """Test error formatting with no context."""
        message = "Something went wrong"
        context = {}
        result = format_error_message(message, context)
        
        assert result == "Error: Something went wrong"


class TestFileSystemError:
    """Test FileSystemError exception class."""
    
    def test_filesystem_error_basic(self):
        """Test basic FileSystemError creation."""
        error = FileSystemError("File not found")
        assert "Error: File not found" in str(error)
    
    def test_filesystem_error_with_context(self):
        """Test FileSystemError with context."""
        error = FileSystemError(
            "File not found",
            {"file_path": "/path/to/file.mkv"}
        )
        assert "Error: File not found" in str(error)
        assert "File: /path/to/file.mkv" in str(error)
        assert error.context["file_path"] == "/path/to/file.mkv"


class TestDependencyError:
    """Test DependencyError exception class."""
    
    def test_dependency_error_basic(self):
        """Test basic DependencyError creation."""
        error = DependencyError("ffmpeg not found")
        assert "Error: ffmpeg not found" in str(error)
    
    def test_dependency_error_with_context(self):
        """Test DependencyError with context."""
        error = DependencyError(
            "External tool failed",
            {"dependency": "ffmpeg", "cause": "Command not found"}
        )
        assert "Error: External tool failed" in str(error)
        assert "Tool: ffmpeg" in str(error)
        assert "Cause: Command not found" in str(error)


class TestValidationError:
    """Test ValidationError exception class."""
    
    def test_validation_error_basic(self):
        """Test basic ValidationError creation."""
        error = ValidationError("Invalid chapter data")
        assert "Error: Invalid chapter data" in str(error)
    
    def test_validation_error_with_context(self):
        """Test ValidationError with context."""
        error = ValidationError(
            "Invalid timestamps",
            {"operation": "validate_chapters", "cause": "Timestamps not in order"}
        )
        assert "Error: Invalid timestamps" in str(error)
        assert "Operation: validate_chapters" in str(error)
        assert "Cause: Timestamps not in order" in str(error)


class TestProcessingError:
    """Test ProcessingError exception class."""
    
    def test_processing_error_basic(self):
        """Test basic ProcessingError creation."""
        error = ProcessingError("Transcription failed")
        assert "Error: Transcription failed" in str(error)
    
    def test_processing_error_with_context(self):
        """Test ProcessingError with context."""
        error = ProcessingError(
            "Transcription failed",
            {
                "file_path": "/path/to/audio.mp3",
                "dependency": "whisper",
                "cause": "Model loading failed"
            }
        )
        assert "Error: Transcription failed" in str(error)
        assert "File: /path/to/audio.mp3" in str(error)
        assert "Tool: whisper" in str(error)
        assert "Cause: Model loading failed" in str(error)


class TestErrorInheritance:
    """Test that all custom errors inherit from base exception."""
    
    def test_all_errors_inherit_from_base(self):
        """Test that all custom errors are instances of MeetingVideoChapterError."""
        assert issubclass(FileSystemError, MeetingVideoChapterError)
        assert issubclass(DependencyError, MeetingVideoChapterError)
        assert issubclass(ValidationError, MeetingVideoChapterError)
        assert issubclass(ProcessingError, MeetingVideoChapterError)
    
    def test_all_errors_are_exceptions(self):
        """Test that all custom errors are instances of Exception."""
        assert issubclass(FileSystemError, Exception)
        assert issubclass(DependencyError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(ProcessingError, Exception)
